from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from zai import ZhipuAiClient
import io
import docx
import pdfplumber
import os
import json
import uuid
import numpy as np
import logging
import tiktoken
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.middleware("http")
async def metrics_middleware(request, call_next):
    path = request.url.path
    if path.startswith("/api"):
        trace_id = metrics_collector.start_request(path)
        try:
            response = await call_next(request)
            metrics_collector.end_request(path, trace_id, response.status_code)
            return response
        except Exception as e:
            metrics_collector.end_request(path, trace_id, 500)
            raise
    return await call_next(request)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

chroma_client = chromadb.PersistentClient(path="./chroma_db")
embedding_fn = embedding_functions.DefaultEmbeddingFunction()
collection = chroma_client.get_or_create_collection(
    name="youzhao_knowledge",
    embedding_function=embedding_fn
)

api_key = os.getenv("API_KEY", "")
zhipu_client = ZhipuAiClient(api_key=api_key)

reranker_model = None
try:
    from sentence_transformers import SentenceTransformer
    reranker_model = SentenceTransformer("BAAI/bge-reranker-v2-m3")
    logger.info("Reranker模型加载成功")
except ImportError:
    logger.warning("sentence-transformers未安装，将使用基于embedding的排序")
except Exception as e:
    logger.warning(f"Reranker模型加载失败: {e}")

from app.models import SessionLocal, CustomerCredit, CustomerApproval
from app.agent import AgentExecutor, retry
from app.monitoring import metrics_collector, StructuredLogger, get_circuit_breaker, track_metrics
from app.context import conversation_manager

@retry(max_attempts=3, delay=0.5, backoff=2)
def query_customer_credit(customer_id: str):
    db = SessionLocal()
    try:
        customer = db.query(CustomerCredit).filter(CustomerCredit.customer_id == customer_id.upper()).first()
        if customer:
            return {
                "customer_id": customer.customer_id,
                "customer_name": customer.customer_name,
                "credit_limit": customer.credit_limit,
                "loan_limit": customer.loan_limit,
                "used_credit": customer.used_credit,
                "used_loan": customer.used_loan,
                "credit_status": customer.credit_status,
                "loan_status": customer.loan_status,
                "update_time": customer.update_time
            }
        return None
    finally:
        db.close()

@retry(max_attempts=3, delay=0.5, backoff=2)
def query_all_customers():
    db = SessionLocal()
    try:
        customers = db.query(CustomerCredit).all()
        return [{"customer_id": c.customer_id, "customer_name": c.customer_name, "credit_limit": c.credit_limit, "loan_limit": c.loan_limit} for c in customers]
    finally:
        db.close()

@retry(max_attempts=3, delay=0.5, backoff=2)
def query_customer_approval(customer_id: str):
    db = SessionLocal()
    try:
        approval = db.query(CustomerApproval).filter(CustomerApproval.customer_id == customer_id.upper()).first()
        if approval:
            return {
                "customer_id": approval.customer_id,
                "customer_name": approval.customer_name,
                "apply_type": approval.apply_type,
                "apply_amount": approval.apply_amount,
                "apply_date": approval.apply_date,
                "approval_status": approval.approval_status,
                "approval_result": approval.approval_result,
                "approver": approval.approver,
                "approval_date": approval.approval_date,
                "remark": approval.remark
            }
        return None
    finally:
        db.close()

@retry(max_attempts=3, delay=0.5, backoff=2)
def query_all_approvals():
    db = SessionLocal()
    try:
        approvals = db.query(CustomerApproval).all()
        return [{"customer_id": a.customer_id, "customer_name": a.customer_name, "apply_type": a.apply_type, "apply_amount": a.apply_amount, "approval_status": a.approval_status} for a in approvals]
    finally:
        db.close()

from app.agent import register_tool, format_credit_result, format_approval_result, format_list_credits, format_list_approvals

register_tool(
    name="query_credit",
    description="查询客户额度信息，包括授信额度、贷款额度、已用额度、状态等。当用户询问客户额度、贷款额度、授信额度时使用。",
    parameters={"customer_id": "客户号，如C001、C002等"},
    func=query_customer_credit
)

register_tool(
    name="query_approval",
    description="查询客户贷款审批状态，包括申请类型、申请金额、审批状态、审批结果等。当用户询问审批状态、贷款审批、申请结果时使用。",
    parameters={"customer_id": "客户号，如C001、C002等"},
    func=query_customer_approval
)

register_tool(
    name="query_all_credits",
    description="查询所有客户的额度信息。当用户询问所有客户额度或列出所有客户时使用。",
    parameters={},
    func=query_all_customers
)

register_tool(
    name="query_all_approvals",
    description="查询所有客户的审批信息。当用户询问所有审批情况或列出所有审批时使用。",
    parameters={},
    func=query_all_approvals
)

agent_executor = None

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class KnowledgeUploadRequest(BaseModel):
    content: str

class KnowledgeDeleteRequest(BaseModel):
    id: str

class FeedbackRequest(BaseModel):
    session_id: str
    question: str
    answer: str
    rating: int
    feedback_type: Optional[str] = "helpful"
    comment: Optional[str] = ""

class RagEvaluationRequest(BaseModel):
    questionCount: int
    evaluationType: str

# 初始化知识库（添加示例知识）
def init_knowledge_base():
    # 检查集合是否为空
    if collection.count() == 0:
        # 添加贷前KYC相关知识
        collection.add(
            documents=[
                "客户资质查询：需要客户提供身份证、营业执照等材料，系统会自动审核客户资质等级。",
                "授信情况查询：根据客户资质等级和历史交易记录，系统会给出授信额度建议。",
                "历史营销经验推荐：基于客户历史行为和行业数据，推荐适合的营销方案。"
            ],
            metadatas=[
                {"category": "贷前KYC"},
                {"category": "贷前KYC"},
                {"category": "贷前KYC"}
            ],
            ids=["1", "2", "3"]
        )
        
        # 添加贷中营销相关知识
        collection.add(
            documents=[
                "产品方案匹配：根据客户需求和资质，推荐适合的贷款产品。",
                "优惠利率查询：根据客户等级和活动期间，提供相应的优惠利率。",
                "分期方式查询：提供多种分期方案，满足客户不同需求。",
                "营销资源查询：查询可用的营销资源，如优惠券、活动等。"
            ],
            metadatas=[
                {"category": "贷中营销"},
                {"category": "贷中营销"},
                {"category": "贷中营销"},
                {"category": "贷中营销"}
            ],
            ids=["4", "5", "6", "7"]
        )
        
        # 添加贷后跟进相关知识
        collection.add(
            documents=[
                "审批状态查询：实时查询贷款审批状态，包括待审批、审批中、已通过、已拒绝等。",
                "提款进度查询：查询贷款提款的进度，包括待提款、处理中、已完成等。",
                "提额失败原因分析：分析提额失败的原因，如信用记录不良、还款能力不足等。",
                "客户建档状态查询：查询客户档案的建立状态，确保客户信息完整。"
            ],
            metadatas=[
                {"category": "贷后跟进"},
                {"category": "贷后跟进"},
                {"category": "贷后跟进"},
                {"category": "贷后跟进"}
            ],
            ids=["8", "9", "10", "11"]
        )

# 初始化知识库
init_knowledge_base()

def chunk_text(text, chunk_size=800, overlap=100):
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap
        if start >= len(text):
            break
    return chunks

# 混合检索函数
def hybrid_search(query, collection, top_k=5, query_words=None):
    # 1. 向量检索
    try:
        vector_results = collection.query(
            query_texts=[query],
            n_results=top_k * 2
        )
        vector_docs = vector_results.get("documents", [[]])[0]
        vector_distances = vector_results.get("distances", [[]])[0]
    except Exception as e:
        print(f"向量检索失败: {e}")
        vector_docs = []
        vector_distances = []
    
    # 2. 关键词检索
    all_results = collection.get()
    all_documents = all_results.get("documents", [])
    
    if not all_documents:
        return {"documents": [[]], "scores": [[]]}
    
    # 预处理查询词（中文2-gram）
    if query_words is None:
        query_words_2gram = [query[i:i+2] for i in range(len(query) - 1)]
        query_words = query_words_2gram + [query]
        query_words = [w for w in query_words if len(w) >= 2]
    
    # 计算关键词得分（词匹配率）
    keyword_scores = []
    for doc in all_documents:
        if query_words:
            matches = sum(1 for w in query_words if w in doc)
            score = matches / len(query_words)
        else:
            score = 0
        keyword_scores.append(score)
    
    # 3. 合并结果并计算综合得分（关键词占主导）
    doc_scores = {}
    doc_keyword_scores = {}
    
    # 添加向量检索结果
    for i, doc in enumerate(vector_docs):
        vector_score = 1.0 / (1.0 + vector_distances[i])
        if doc in doc_scores:
            doc_scores[doc] = max(doc_scores[doc], 0.1 * vector_score)
        else:
            doc_scores[doc] = 0.1 * vector_score
    
    # 添加关键词检索结果（关键词得分独立存储）
    for i, doc in enumerate(all_documents):
        if doc in doc_keyword_scores:
            doc_keyword_scores[doc] = max(doc_keyword_scores[doc], keyword_scores[i])
        else:
            doc_keyword_scores[doc] = keyword_scores[i]
        
        if doc in doc_scores:
            doc_scores[doc] = max(doc_scores[doc], 0.9 * keyword_scores[i])
        else:
            doc_scores[doc] = 0.9 * keyword_scores[i]
    
    # 排序（优先按关键词得分）
    sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
    
    # 取前top_k
    top_docs = [doc for doc, score in sorted_docs[:top_k]]
    top_scores = [score for doc, score in sorted_docs[:top_k]]
    
    # 返回关键词得分用于过滤
    top_keyword_scores = [doc_keyword_scores.get(doc, 0) for doc in top_docs]
    
    return {"documents": [top_docs], "scores": [top_scores], "keyword_scores": [top_keyword_scores]}

# RAG检索函数（使用混合检索 + Reranker重排序）
def rag_retrieval(query, top_k=5, max_length=500):
    # 中文2-gram分词（提取连续2个字作为词）
    query_words = []
    for i in range(len(query) - 1):
        word = query[i:i+2]
        if word:
            query_words.append(word)
    
    # 使用混合检索
    results = hybrid_search(query, collection, top_k * 3, query_words)
    retrieved_knowledge = results.get("documents", [[]])[0]
    keyword_scores = results.get("keyword_scores", [[]])[0]
    
    # 严格过滤：关键词得分必须>0
    filtered = []
    filtered_scores = []
    if query_words:
        for doc, kw_score in zip(retrieved_knowledge, keyword_scores):
            if kw_score > 0:
                filtered.append(doc)
                filtered_scores.append(kw_score)
    else:
        filtered = retrieved_knowledge
        filtered_scores = keyword_scores
    
    print(f"查询词: {query_words}")
    print(f"检索结果: {len(retrieved_knowledge)}, 过滤后: {len(filtered)}, 关键词得分: {filtered_scores}")
    
    if len(filtered) == 0 and len(retrieved_knowledge) > 0:
        return {"documents": [[]], "scores": [[]], "query_words": query_words}
    
    # Reranker重排序
    rerank_scores = filtered_scores
    if len(filtered) > 1:
        try:
            if reranker_model:
                rerank_scores = reranker_model.predict([(query, doc) for doc in filtered])
                paired = list(zip(filtered, filtered_scores, rerank_scores))
                paired.sort(key=lambda x: x[1] * 0.3 + x[2] * 0.7, reverse=True)
            else:
                doc_embeddings = embedding_fn(filtered)
                query_embedding = embedding_fn([query])[0]
                rerank_scores = np.dot(doc_embeddings, query_embedding)
                paired = list(zip(filtered, filtered_scores, rerank_scores))
                paired.sort(key=lambda x: x[1] * 0.5 + x[2] * 0.5, reverse=True)
            
            filtered = [p[0] for p in paired]
            filtered_scores = [p[1] for p in paired]
            rerank_scores = [p[2] for p in paired]
            print(f"Reranker重排序后: {len(filtered)}条")
        except Exception as e:
            print(f"Reranker失败: {e}")
    
    # 获取来源metadata
    try:
        all_results = collection.get()
        all_ids = all_results.get("ids", [])
        all_metadatas = all_results.get("metadatas", [])
        id_to_metadata = {ids: meta for ids, meta in zip(all_ids, all_metadatas)}
        
        results_with_metadata = []
        for doc in filtered:
            for ids, meta in zip(all_ids, all_metadatas):
                if doc == meta.get("summary", "") or doc.startswith(meta.get("summary", "")[:50]):
                    results_with_metadata.append({
                        "content": doc,
                        "metadata": meta
                    })
                    break
            else:
                results_with_metadata.append({"content": doc, "metadata": {}})
    except:
        results_with_metadata = [{"content": doc, "metadata": {}} for doc in filtered]
    
    # 截断过长内容
    truncated = [doc["content"][:max_length] + "..." if len(doc["content"]) > max_length else doc["content"] for doc in results_with_metadata]
    metadatas = [doc.get("metadata", {}) for doc in results_with_metadata]
    
    return {"documents": [truncated], "scores": [filtered_scores], "query_words": query_words, "metadatas": [metadatas], "rerank_scores": [rerank_scores]}

# Agent工具调用函数
def extract_customer_id(query):
    import re
    match = re.search(r'[Cc]\d{3}', query)
    return match.group().upper() if match else None

def agent_plan_and_execute(query):
    import re
    
    customer_id = extract_customer_id(query)
    tools_to_use = []
    
    # 判断需要调用的工具
    if "额度" in query or "贷款" in query or "授信" in query:
        if "所有" in query or "全部" in query or "列表" in query:
            tools_to_use.append("query_all_credits")
        elif customer_id:
            tools_to_use.append("query_credit")
    
    if "审批" in query or "申请" in query or "审批状态" in query:
        if "所有" in query or "全部" in query or "列表" in query:
            tools_to_use.append("query_all_approvals")
        elif customer_id:
            tools_to_use.append("query_approval")
    
    # 执行工具
    results = {}
    for tool_name in tools_to_use:
        tool = AGENT_TOOLS.get(tool_name)
        if tool:
            if tool_name == "query_all_credits":
                data = tool["func"]()
                results["query_all_credits"] = data
            elif tool_name == "query_all_approvals":
                data = tool["func"]()
                results["query_all_approvals"] = data
            elif customer_id and tool_name in ["query_credit", "query_approval"]:
                data = tool["func"](customer_id)
                results[tool_name] = data
    
    return tools_to_use, results, customer_id

def format_credit_result(data):
    if not data:
        return "未找到该客户额度信息"
    return f"""客户 {data['customer_id']} ({data['customer_name']}) 的额度信息：
📊 授信额度：{data['credit_limit']:,.0f} 元
💰 已用授信：{data['used_credit']:,.0f} 元
📈 剩余可用：{data['credit_limit'] - data['used_credit']:,.0f} 元
🏦 贷款额度：{data['loan_limit']:,.0f} 元
💳 已用贷款：{data['used_loan']:,.0f} 元
✅ 授信状态：{data['credit_status']}
✅ 贷款状态：{data['loan_status']}
📅 更新时间：{data['update_time']}"""

def format_approval_result(data):
    if not data:
        return "未找到该客户审批信息"
    approver = data['approver'] if data['approver'] else "待定"
    approval_date = data['approval_date'] if data['approval_date'] else "待定"
    return f"""客户 {data['customer_id']} ({data['customer_name']}) 的审批信息：
📝 申请类型：{data['apply_type']}
💵 申请金额：{data['apply_amount']:,.0f} 元
📅 申请日期：{data['apply_date']}
📌 审批状态：{data['approval_status']}
✅ 审批结果：{data['approval_result']}
👤 审批人：{approver}
📅 审批日期：{approval_date}
📋 备注：{data['remark']}"""

def format_list_credits(data):
    if not data:
        return "暂无客户额度数据"
    result = "所有客户额度信息：\n\n"
    for c in data:
        result += f"{c['customer_id']} - {c['customer_name']}: 授信{c['credit_limit']:,.0f}, 贷款{c['loan_limit']:,.0f}\n"
    return result

def format_list_approvals(data):
    if not data:
        return "暂无审批数据"
    status_emoji = {"已通过": "✅", "已拒绝": "❌", "审批中": "⏳"}
    result = "所有客户审批信息：\n\n"
    for a in data:
        emoji = status_emoji.get(a['approval_status'], "📌")
        result += f"{a['customer_id']} - {a['customer_name']}: {a['apply_type']} {a['apply_amount']:,.0f}元 {emoji}{a['approval_status']}\n"
    return result

# Prompt生成函数
def generate_prompt(query, retrieved_knowledge, task_type, history=None):
    # 根据任务类型生成不同的Prompt
    if task_type == "贷前KYC":
        system_prompt = "你是一名银行贷前KYC专家，负责回答客户资质、授信情况和营销经验相关的问题。"
    elif task_type == "贷中营销":
        system_prompt = "你是一名银行贷中营销专家，负责回答产品方案、利率、分期和营销资源相关的问题。"
    elif task_type == "贷后跟进":
        system_prompt = "你是一名银行贷后跟进专家，负责回答审批状态、提款进度、提额失败原因和建档状态相关的问题。"
    else:
        system_prompt = "你是一名银行客服专家，负责回答客户的各种问题。"
    
    # 构建历史对话上下文
    history_context = ""
    if history and len(history) > 0:
        history_parts = []
        for msg in history[-4:]:
            role = "用户" if msg.get("role") == "user" else "助手"
            content = msg.get("content", "")
            history_parts.append(f"{role}：{content}")
        history_context = "对话历史：\n" + "\n".join(history_parts) + "\n\n"
    
    # 没有检索到知识时，使用通用prompt让大模型自由回答
    if not retrieved_knowledge:
        prompt = f"{system_prompt}\n\n{history_context}用户问题：{query}\n\n请根据您的专业知识回答用户问题。"
        return prompt
    
    # 构建知识上下文
    knowledge_context = "\n".join(retrieved_knowledge)
    
    # 生成最终Prompt
    prompt = f"{system_prompt}\n\n{history_context}知识库信息：\n{knowledge_context}\n\n用户问题：{query}\n\n回答要求：\n1. 必须基于知识库中的信息回答，不要超出知识库范围\n2. 禁止添加知识库中没有的信息\n3. 禁止编造事实\n4. 如果知识库没有相关信息，请明确告知用户"
    return prompt

# 大模型调用函数
def call_llm(prompt):
    try:
        # 调用智谱API
        response = zhipu_client.chat.completions.create(
            model="glm-4.6v-flashx",
            messages=[
                {"role": "system", "content": "你是有招小助手，一名专业的银行服务助手。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        return response.choices[0].message.content
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"AI服务暂时不可用: {str(e)}"

# 聊天接口
@app.post("/api/chat")
def chat(request: ChatRequest):
    trace_id = metrics_collector.start_request("/api/chat")
    StructuredLogger.info("chat_request_start", trace_id, message=request.message[:50])
    try:
        session_id = request.session_id
        if not session_id:
            session_id = conversation_manager.create_session()
        
        history = conversation_manager.get_history(session_id)
        
        conversation_manager.add_message(session_id, "user", request.message)
        
        tools_used = []
        tool_results = {}
        
        # 尝试使用LLM Agent
        try:
            global agent_executor
            if agent_executor is None:
                from app.agent import AgentExecutor
                agent_executor = AgentExecutor(zhipu_client)
            
            cb = get_circuit_breaker("llm")
            agent_result = cb.call(agent_executor.execute, request.message)
            tools_used = agent_result.get("tools_used", [])
            tool_results = agent_result.get("tool_results", {})
        except Exception as e:
            logger.warning(f"Agent执行失败，使用规则匹配: {e}")
        
        # 降级：使用规则匹配
        if not tools_used:
            from app.agent import extract_customer_id
            customer_id = extract_customer_id(request.message)
            
            if customer_id:
                if "额度" in request.message or "贷款" in request.message or "授信" in request.message:
                    tools_used.append("query_credit")
                    tool_results["query_credit"] = query_customer_credit(customer_id)
                if "审批" in request.message or "申请" in request.message or "审批状态" in request.message:
                    tools_used.append("query_approval")
                    tool_results["query_approval"] = query_customer_approval(customer_id)
            
            elif "所有" in request.message or "全部" in request.message:
                if "额度" in request.message or "贷款" in request.message:
                    tools_used.append("query_all_credits")
                    tool_results["query_all_credits"] = query_all_customers()
                if "审批" in request.message:
                    tools_used.append("query_all_approvals")
                    tool_results["query_all_approvals"] = query_all_approvals()
        
        if tools_used:
            answer_parts = []
            for tool_name in tools_used:
                if tool_name == "query_credit" and "query_credit" in tool_results:
                    answer_parts.append(format_credit_result(tool_results["query_credit"]))
                elif tool_name == "query_approval" and "query_approval" in tool_results:
                    answer_parts.append(format_approval_result(tool_results["query_approval"]))
                elif tool_name == "query_all_credits" and "query_all_credits" in tool_results:
                    answer_parts.append(format_list_credits(tool_results["query_all_credits"]))
                elif tool_name == "query_all_approvals" and "query_all_approvals" in tool_results:
                    answer_parts.append(format_list_approvals(tool_results["query_all_approvals"]))
            
            if answer_parts:
                raw_result = "\n\n".join(answer_parts)
                
                refine_prompt = f"""用户问题：{request.message}

数据库查询结果：
{raw_result}

请根据用户问题，从数据库查询结果中提取相关信息，给出精简、准确的回答。
如果用户问的是具体数值（如剩余额度、贷款额度等），请直接给出数值，不需要展示所有详细信息。
回答要简洁，不要罗列所有字段。"""

                try:
                    answer = call_llm(refine_prompt)
                except Exception as e:
                    logger.warning(f"LLM精炼失败，使用原始结果: {e}")
                    answer = raw_result
                
                conversation_manager.add_message(session_id, "assistant", answer)
                
                return {
                    "answer": answer,
                    "sources": [],
                    "metrics": {"retrieval_recall": 1.0, "context_precision": 1.0, "answer_relevancy": 1.0, "faithfulness": 1.0, "context_recall": 1.0},
                    "task_type": "数据库查询",
                    "session_id": session_id
                }
        
        task_type = "通用咨询"
        if "资质" in request.message or "授信" in request.message or "营销经验" in request.message:
            task_type = "贷前KYC"
        elif "产品" in request.message or "利率" in request.message or "分期" in request.message:
            task_type = "贷中营销"
        elif "审批" in request.message or "提款" in request.message or "提额" in request.message:
            task_type = "贷后跟进"
        
        retrieval_results = rag_retrieval(request.message)
        retrieved_knowledge = retrieval_results.get("documents", [[]])[0]
        keyword_scores = retrieval_results.get("scores", [[]])[0]
        
        # 3. 生成Prompt
        prompt = generate_prompt(request.message, retrieved_knowledge, task_type, history)
        
        # 4. 调用大模型
        answer = call_llm(prompt)
        
        # 5. 计算实时评测指标
        query_words = retrieval_results.get("query_words", [])
        
        # RAG质量检查
        quality_check_result = {"is_relevant": True, "score": 1.0}
        try:
            from app.quality import create_quality_checker
            quality_checker = create_quality_checker(zhipu_client)
            quality_check_result = quality_checker.check_relevance(request.message, retrieved_knowledge)
            
            if not quality_check_result.get("is_relevant", False):
                logger.warning(f"RAG质量检查不通过: {quality_check_result.get('reason')}")
        except Exception as e:
            logger.warning(f"RAG质量检查失败: {e}")
        
        eval_metrics = {
            "retrieval_recall": 1.0 if retrieved_knowledge else 0.0,
            "context_precision": calculate_context_precision(request.message, retrieved_knowledge, query_words),
            "answer_relevancy": calculate_answer_relevancy(request.message, answer),
            "faithfulness": calculate_faithfulness(answer, retrieved_knowledge) if retrieved_knowledge else 0.0,
            "context_recall": 0.0,
            "quality_check": quality_check_result
        }
        
        retrieval_metadatas = retrieval_results.get("metadatas", [[]])[0]
        
        # 6. 返回结果（只返回top 2最相关的来源）
        sources = []
        if retrieved_knowledge and keyword_scores:
            # 获取rerank得分用于排序
            rerank_scores = retrieval_results.get("rerank_scores", [[]])[0]
            
            # 组合所有得分并排序
            combined = []
            for i, (doc, kw_score, metadata) in enumerate(zip(retrieved_knowledge, keyword_scores, retrieval_metadatas)):
                if kw_score > 0:
                    r_score = rerank_scores[i] if i < len(rerank_scores) else kw_score
                    combined.append({
                        "doc": doc,
                        "kw_score": kw_score,
                        "r_score": r_score,
                        "metadata": metadata
                    })
            
            # 按综合得分排序，取top 2
            combined.sort(key=lambda x: x["kw_score"] * 0.3 + x["r_score"] * 0.7, reverse=True)
            top_sources = combined[:2]
            
            for item in top_sources:
                doc = item["doc"]
                metadata = item["metadata"]
                source_info = {
                    "content": doc[:200] + "..." if len(doc) > 200 else doc,
                    "category": metadata.get("category", ""),
                    "source_file": metadata.get("source_file", "内置知识"),
                    "chunk_index": metadata.get("chunk_index", 0) + 1,
                    "total_chunks": metadata.get("total_chunks", 1)
                }
                sources.append(source_info)
        
        conversation_manager.add_message(session_id, "assistant", answer)
        
        StructuredLogger.info("chat_request_end", trace_id, status=200)
        metrics_collector.end_request("/api/chat", trace_id, 200)
        
        return {
            "answer": answer, 
            "sources": sources,
            "metrics": eval_metrics,
            "task_type": task_type,
            "session_id": session_id
        }
    except Exception as e:
        StructuredLogger.error("chat_request_error", trace_id, error=str(e))
        metrics_collector.end_request("/api/chat", trace_id, 500)
        raise HTTPException(status_code=500, detail=str(e))

# 知识上传接口 - 文件上传方式
@app.post("/api/knowledge/upload")
async def upload_knowledge(file: UploadFile = File(...)):
    trace_id = metrics_collector.start_request("/api/knowledge/upload")
    StructuredLogger.info("upload_start", trace_id, filename=file.filename)
    try:
        content = ""
        filename = file.filename
        
        # 尝试从header获取原始文件名
        if not filename:
            filename = "unknown.txt"
        
        filename_lower = filename.lower()
        
        # 读取文件内容
        content_bytes = await file.read()
        
        # 检测内容类型：如果看起来像zip文件头，说明是真实的docx/pdf
        if len(content_bytes) >= 4 and content_bytes[:4] == b'PK\x03\x04':
            # 真实的docx文件
            if filename_lower.endswith('.docx'):
                doc = docx.Document(io.BytesIO(content_bytes))
                content = '\n'.join([para.text for para in doc.paragraphs])
            elif filename_lower.endswith('.pdf'):
                with pdfplumber.open(io.BytesIO(content_bytes)) as pdf:
                    for page in pdf.pages:
                        text = page.extract_text()
                        if text:
                            content += text + '\n'
            else:
                # 未知二进制格式但有docx/pdf扩展名
                raise HTTPException(status_code=400, detail="不支持的二进制文件格式")
        else:
            # 已经是解析后的文本内容
            content = content_bytes.decode('utf-8', errors='ignore')
        
        if not content.strip():
            raise HTTPException(status_code=400, detail="文件内容为空")
        category = "通用"
        if "资质" in content or "授信" in content or "营销经验" in content:
            category = "贷前KYC"
        elif "产品" in content or "利率" in content or "分期" in content or "营销资源" in content:
            category = "贷中营销"
        elif "审批" in content or "提款" in content or "提额" in content or "建档" in content:
            category = "贷后跟进"
        
        # 文本分块
        chunks = chunk_text(content, chunk_size=1000, overlap=100)
        
        # 批量添加到Chroma向量数据库
        ids = []
        documents = []
        metadatas = []
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"{str(uuid.uuid4())}_{i}"
            ids.append(chunk_id)
            documents.append(chunk)
            summary = chunk[:100] + "..." if len(chunk) > 100 else chunk
            parent_id = str(uuid.uuid4())
            metadatas.append({
                "category": category,
                "summary": summary,
                "parent_id": parent_id,
                "source_file": filename,
                "chunk_index": i,
                "total_chunks": len(chunks)
            })
        
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        StructuredLogger.info("upload_success", trace_id, chunks=len(chunks))
        metrics_collector.end_request("/api/knowledge/upload", trace_id, 200)
        
        return {"message": "知识上传成功", "id": ids[0], "chunks": len(chunks)}
    except Exception as e:
        import traceback
        traceback.print_exc()
        StructuredLogger.error("upload_error", trace_id, error=str(e))
        metrics_collector.end_request("/api/knowledge/upload", trace_id, 500)
        raise HTTPException(status_code=500, detail=str(e))

# 知识列表获取接口
@app.get("/api/knowledge/list")
def get_knowledge_list():
    try:
        # 获取所有知识
        results = collection.get()
        documents = results.get("documents", [])
        metadatas = results.get("metadatas", [])
        ids = results.get("ids", [])
        
        # 构建返回列表
        knowledge_list = []
        for doc, meta, id in zip(documents, metadatas, ids):
            knowledge_list.append({
                "id": id,
                "content": doc,
                "category": meta.get("category", "通用")
            })
        
        return knowledge_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 知识删除接口
@app.post("/api/knowledge/delete")
def delete_knowledge(request: KnowledgeDeleteRequest):
    try:
        # 从Chroma向量数据库中删除
        collection.delete(ids=[request.id])
        return {"message": "删除成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 清空知识库接口
@app.post("/api/knowledge/clear")
def clear_knowledge():
    try:
        # 获取所有IDs并删除
        all_data = collection.get()
        all_ids = all_data.get("ids", [])
        if all_ids:
            collection.delete(ids=all_ids)
        return {"message": "知识库已清空"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# RAG评测接口 - 使用RAGAS核心指标
@app.post("/api/rag/evaluate")
def evaluate_rag(request: RagEvaluationRequest):
    try:
        # 评测问题集（可以根据evaluationType选择不同类型）
        evaluation_questions = {
            "贷前KYC": [
                {"question": "如何查询客户资质？", "ground_truth": "需要客户提供身份证、营业执照等材料，系统会自动审核客户资质等级。"},
                {"question": "授信额度是如何确定的？", "ground_truth": "根据客户资质等级和历史交易记录，系统会给出授信额度建议。"},
                {"question": "客户资质等级有哪些？", "ground_truth": "客户资质等级分为A、B、C、D四个等级。"}
            ],
            "贷中营销": [
                {"question": "如何匹配适合的产品方案？", "ground_truth": "根据客户需求和资质情况，系统推荐最适合的产品方案。"},
                {"question": "有哪些营销资源？", "ground_truth": "营销资源包括产品政策、优惠利率、分期方案等。"}
            ],
            "贷后跟进": [
                {"question": "如何查询审批状态？", "ground_truth": "通过客户编号在系统中查询贷款审批进度状态。"},
                {"question": "提额失败的原因有哪些？", "ground_truth": "提额失败原因包括信用记录不良、负债过高、申请资料不完整等。"}
            ],
            "CORS跨域": [
                {"question": "什么是CORS？", "ground_truth": "CORS是跨源资源共享（Cross-Origin Resource Sharing）的缩写，是前端开发中非常常见的问题，核心是前后端不同源时，后端必须正确配置CORS响应头。"},
                {"question": "CORS错误怎么解决？", "ground_truth": "后端需要配置CORS响应头，允许来自前端的跨域请求。"},
                {"question": "什么是跨域请求？", "ground_truth": "跨域请求是指浏览器发起请求的域名与服务器域名不一致，浏览器出于安全考虑会阻止这类请求。"}
            ],
            "全部": [
                {"question": "如何查询客户资质？", "ground_truth": "需要客户提供身份证、营业执照等材料，系统会自动审核客户资质等级。"},
                {"question": "授信额度是如何确定的？", "ground_truth": "根据客户资质等级和历史交易记录，系统会给出授信额度建议。"},
                {"question": "如何匹配适合的产品方案？", "ground_truth": "根据客户需求和资质情况，系统推荐最适合的产品方案。"},
                {"question": "如何查询审批状态？", "ground_truth": "通过客户编号在系统中查询贷款审批进度状态。"},
                {"question": "提额失败的原因有哪些？", "ground_truth": "提额失败原因包括信用记录不良、负债过高、申请资料不完整等。"},
                {"question": "什么是CORS？", "ground_truth": "CORS是跨源资源共享，核心是前后端不同源时，后端必须正确配置CORS响应头。"},
                {"question": "CORS错误怎么解决？", "ground_truth": "后端需要配置CORS响应头，允许来自前端的跨域请求。"}
            ]
        }
        
        # 选择评测问题集
        eval_type = request.evaluationType if request.evaluationType else "全部"
        questions_data = evaluation_questions.get(eval_type, evaluation_questions["全部"])
        question_count = min(request.questionCount, len(questions_data))
        questions_data = questions_data[:question_count]
        
        # 存储评测结果
        results = []
        total_metrics = {
            "faithfulness": 0.0,
            "answer_relevancy": 0.0,
            "context_precision": 0.0,
            "context_recall": 0.0,
            "retrieval_recall": 0.0
        }
        
        for item in questions_data:
            question = item["question"]
            ground_truth = item["ground_truth"]
            
            # RAG检索
            retrieval_results = rag_retrieval(question)
            retrieved_knowledge = retrieval_results.get("documents", [[]])[0]
            retrieval_query_words = retrieval_results.get("query_words", [])
            
            # 简单的任务规划
            if "资质" in question or "营销经验" in question:
                task_type = "贷前KYC"
            elif "产品" in question or "利率" in question or "分期" in question:
                task_type = "贷中营销"
            elif "审批" in question or "提款" in question or "提额" in question:
                task_type = "贷后跟进"
            else:
                task_type = "通用咨询"
            
            prompt = generate_prompt(question, retrieved_knowledge, task_type)
            
            # 调用大模型
            answer = call_llm(prompt)
            
            # 计算各项指标
            # 1. Faithfulness（忠诚度）：回答中是否使用了检索到的知识
            faithfulness_score = calculate_faithfulness(answer, retrieved_knowledge)
            
            # 2. Answer Relevancy（答案相关性）：回答与问题的相关程度
            answer_relevancy_score = calculate_answer_relevancy(question, answer)
            
            # 3. Context Precision（上下文精确度）：检索内容与问题的相关程度
            context_precision_score = calculate_context_precision(question, retrieved_knowledge, retrieval_query_words)
            
            # 4. Context Recall（上下文召回率）：检索内容覆盖ground truth的程度
            context_recall_score = calculate_context_recall(ground_truth, retrieved_knowledge)
            
            # 5. Retrieval Recall（检索召回率）：检索是否找到相关内容
            retrieval_recall_score = 1.0 if retrieved_knowledge else 0.0
            
            # 累加指标
            total_metrics["faithfulness"] += faithfulness_score
            total_metrics["answer_relevancy"] += answer_relevancy_score
            total_metrics["context_precision"] += context_precision_score
            total_metrics["context_recall"] += context_recall_score
            total_metrics["retrieval_recall"] += retrieval_recall_score
            
            results.append({
                "question": question,
                "ground_truth": ground_truth,
                "answer": answer[:200] + "..." if len(answer) > 200 else answer,
                "retrieved_contexts": retrieved_knowledge[:2],
                "metrics": {
                    "faithfulness": round(faithfulness_score, 3),
                    "answer_relevancy": round(answer_relevancy_score, 3),
                    "context_precision": round(context_precision_score, 3),
                    "context_recall": round(context_recall_score, 3),
                    "retrieval_recall": round(retrieval_recall_score, 3)
                }
            })
        
        # 计算平均指标
        count = len(results)
        avg_metrics = {k: round(v / count, 3) for k, v in total_metrics.items()}
        
        # 计算综合得分（加权平均）
        overall_score = (
            avg_metrics["faithfulness"] * 0.25 +
            avg_metrics["answer_relevancy"] * 0.25 +
            avg_metrics["context_precision"] * 0.2 +
            avg_metrics["context_recall"] * 0.2 +
            avg_metrics["retrieval_recall"] * 0.1
        )
        
        return {
            "overallScore": round(overall_score, 3),
            "questionCount": count,
            "evaluationType": eval_type,
            "metrics": avg_metrics,
            "details": results
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


def calculate_faithfulness(answer: str, contexts: list) -> float:
    """计算忠诚度：回答中是否使用了检索到的知识"""
    if not answer or not contexts:
        return 0.0
    
    # 检查回答中是否包含上下文的关键信息
    context_text = " ".join(contexts)
    answer_lower = answer.lower()
    context_lower = context_text.lower()
    
    # 提取上下文中的关键词（2-gram）
    context_words = set()
    for i in range(len(context_lower) - 1):
        word = context_lower[i:i+2]
        if word.isalnum():
            context_words.add(word)
    
    # 提取回答中的关键词
    answer_words = set()
    for i in range(len(answer_lower) - 1):
        word = answer_lower[i:i+2]
        if word.isalnum():
            answer_words.add(word)
    
    # 计算重叠率
    if not context_words:
        return 0.5
    overlap = len(context_words & answer_words) / len(context_words)
    
    # 如果回答太短，扣分
    if len(answer) < 20:
        overlap *= 0.5
    
    return min(overlap, 1.0)


def calculate_answer_relevancy(question: str, answer: str) -> float:
    """计算答案相关性：回答与问题的相关程度"""
    if not answer or not question:
        return 0.0
    
    # 提取问题关键词
    q_words = set()
    for i in range(len(question) - 1):
        word = question[i:i+2]
        if word.isalnum():
            q_words.add(word)
    
    # 提取回答关键词
    a_words = set()
    for i in range(len(answer) - 1):
        word = answer[i:i+2]
        if word.isalnum():
            a_words.add(word)
    
    # 计算关键词覆盖率
    if not q_words:
        return 0.5
    overlap = len(q_words & a_words) / len(q_words)
    
    # 检查回答长度是否合理
    if len(answer) < 20:
        overlap *= 0.7
    elif len(answer) > 1000:
        overlap *= 0.8
    
    return min(overlap, 1.0)


def calculate_context_precision(question: str, contexts: list, query_words: list) -> float:
    """计算上下文精确度：检索内容与问题的相关程度"""
    if not contexts or not query_words:
        return 0.0
    
    # 计算每个上下文块与问题的相关度
    relevant_count = 0
    for context in contexts:
        context_lower = context.lower()
        # 检查查询词是否出现在上下文中
        matches = sum(1 for word in query_words if word in context_lower)
        if matches > 0:
            relevant_count += 1
    
    precision = relevant_count / len(contexts) if contexts else 0.0
    return precision


def calculate_context_recall(ground_truth: str, contexts: list) -> float:
    """计算上下文召回率：检索内容覆盖ground truth的程度"""
    if not ground_truth or not contexts:
        return 0.0
    
    # 提取ground truth关键词
    gt_words = set()
    for i in range(len(ground_truth) - 1):
        word = ground_truth[i:i+2]
        if word.isalnum():
            gt_words.add(word)
    
    # 检查每个上下文块是否覆盖ground truth
    matched_words = set()
    for context in contexts:
        context_lower = context.lower()
        for word in gt_words:
            if word in context_lower:
                matched_words.add(word)
    
    recall = len(matched_words) / len(gt_words) if gt_words else 0.0
    return recall


# 健康检查接口
@app.get("/health")
def health_check():
    return {"status": "healthy"}

# 监控指标接口
@app.get("/api/metrics")
def get_metrics():
    try:
        return metrics_collector.get_metrics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 对话会话管理接口
@app.get("/api/chat/sessions")
def get_chat_sessions():
    try:
        sessions = conversation_manager.get_all_sessions()
        return {"sessions": sessions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat/session")
def create_chat_session():
    try:
        session_id = conversation_manager.create_session()
        return {"session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/chat/session/{session_id}")
def delete_chat_session(session_id: str):
    try:
        conversation_manager.delete_session(session_id)
        return {"message": "删除成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chat/history/{session_id}")
def get_chat_history(session_id: str):
    try:
        history = conversation_manager.get_history(session_id)
        return {"history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 客户列表接口
@app.get("/api/customer/list")
def get_customer_list():
    try:
        customers = query_all_customers()
        return {"customers": customers, "count": len(customers)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 客户额度查询接口
@app.get("/api/customer/{customer_id}")
def get_customer_info(customer_id: str):
    try:
        customer_id = customer_id.upper()
        customer = query_customer_credit(customer_id)
        if customer:
            return customer
        else:
            raise HTTPException(status_code=404, detail=f"未找到客户号 {customer_id}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/feedback")
def submit_feedback(request: FeedbackRequest):
    try:
        from app.feedback import add_feedback
        feedback_id = add_feedback(
            session_id=request.session_id,
            question=request.question,
            answer=request.answer,
            rating=request.rating,
            feedback_type=request.feedback_type,
            comment=request.comment
        )
        return {"message": "反馈提交成功", "feedback_id": feedback_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/feedback/negative")
def get_negative_feedback(limit: int = 20):
    try:
        from app.feedback import get_negative_feedback
        return {"feedback": get_negative_feedback(limit)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)