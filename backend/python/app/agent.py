import json
import re
import logging
import time
from typing import Dict, List, Any, Optional
from functools import wraps
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

TOOL_REGISTRY = {}

def retry(max_attempts=3, delay=0.5, backoff=2, exceptions=(Exception,)):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            current_delay = delay
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    attempts += 1
                    if attempts >= max_attempts:
                        logger.error(f"{func.__name__} 达到最大重试次数 {max_attempts}, 错误: {e}")
                        raise
                    logger.warning(f"{func.__name__} 第 {attempts} 次失败, 错误: {e}, {current_delay}秒后重试...")
                    time.sleep(current_delay)
                    current_delay *= backoff
            return None
        return wrapper
    return decorator

def register_tool(name: str, description: str, parameters: Dict[str, str], func: callable):
    TOOL_REGISTRY[name] = {
        "name": name,
        "description": description,
        "parameters": parameters,
        "func": func
    }

def get_available_tools() -> List[Dict]:
    return [
        {
            "name": tool["name"],
            "description": tool["description"],
            "parameters": tool["parameters"]
        }
        for tool in TOOL_REGISTRY.values()
    ]

def extract_customer_id(query: str) -> Optional[str]:
    match = re.search(r'[Cc]\d{3}', query)
    return match.group().upper() if match else None

class AgentExecutor:
    def __init__(self, llm_client):
        self.llm_client = llm_client
        self.max_iterations = 5
        
    @retry(max_attempts=3, delay=1, backoff=2)
    def execute(self, query: str) -> Dict[str, Any]:
        tools_used = []
        tool_results = {}
        
        customer_id = extract_customer_id(query)
        
        available_tools = get_available_tools()
        
        system_prompt = f"""你是一个智能助手，负责分析用户问题并选择合适的工具来回答。

可用工具：
{json.dumps(available_tools, ensure_ascii=False, indent=2)}

用户问题：{query}

请分析问题，选择需要调用的工具，并提取工具参数。
如果需要查询客户信息，请从问题中提取客户号（如C001、C002等）。

请以JSON格式返回你的决策：
{{
    "thought": "分析思考过程",
    "tools_to_use": ["工具名1", "工具名2"],  // 需要调用的工具列表
    "parameters": {{  // 每个工具的参数
        "工具名1": {{"参数名": "参数值"}},
        "工具名2": {{"参数名": "参数值"}}
    }},
    "reason": "选择这些工具的原因"
}}

注意：
- 如果问题与客户额度、贷款、授信相关，需要调用query_credit
- 如果问题与审批、申请状态相关，需要调用query_approval  
- 如果用户问"所有"、"全部"、"列表"，需要调用query_all_credits或query_all_approvals
- 如果不需要调用任何工具，返回空列表[]

请只返回JSON，不要其他内容。"""

        response = self.llm_client.chat.completions.create(
            model="glm-4.6v-flashx",
            messages=[
                {"role": "system", "content": "你是一个专业的银行客服助手。"},
                {"role": "user", "content": system_prompt}
            ],
            temperature=0.1
        )
        
        result_text = response.choices[0].message.content
        
        try:
            result_text = result_text.strip()
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
            result_text = result_text.strip()
            
            decision = json.loads(result_text)
        except json.JSONDecodeError as e:
            logger.error(f"LLM返回不是有效JSON: {result_text}, 错误: {e}")
            decision = {"tools_to_use": [], "parameters": {}}
        
        tools_to_call = decision.get("tools_to_use", [])
        parameters = decision.get("parameters", {})
        
        for tool_name in tools_to_call:
            tool = TOOL_REGISTRY.get(tool_name)
            if not tool:
                logger.warning(f"工具 {tool_name} 不存在")
                continue
            
            params = parameters.get(tool_name, {})
            
            if not params and customer_id:
                if tool_name in ["query_credit", "query_approval"]:
                    params = {"customer_id": customer_id}
            
            result = tool["func"](**params)
            tool_results[tool_name] = result
            tools_used.append(tool_name)
            logger.info(f"工具 {tool_name} 执行成功")
        
        return {
            "tools_used": tools_used,
            "tool_results": tool_results,
            "customer_id": customer_id
        }

def format_credit_result(data: Any) -> str:
    if not data:
        return "未找到该客户额度信息"
    if isinstance(data, dict) and "error" in data:
        return f"查询失败: {data['error']}"
    return f"""客户 {data['customer_id']} ({data['customer_name']}) 的额度信息：
📊 授信额度：{data['credit_limit']:,.0f} 元
💰 已用授信：{data['used_credit']:,.0f} 元
📈 剩余可用：{data['credit_limit'] - data['used_credit']:,.0f} 元
🏦 贷款额度：{data['loan_limit']:,.0f} 元
💳 已用贷款：{data['used_loan']:,.0f} 元
✅ 授信状态：{data['credit_status']}
✅ 贷款状态：{data['loan_status']}
📅 更新时间：{data['update_time']}"""

def format_approval_result(data: Any) -> str:
    if not data:
        return "未找到该客户审批信息"
    if isinstance(data, dict) and "error" in data:
        return f"查询失败: {data['error']}"
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

def format_list_credits(data: Any) -> str:
    if not data:
        return "暂无客户额度数据"
    if isinstance(data, dict) and "error" in data:
        return f"查询失败: {data['error']}"
    result = "所有客户额度信息：\n\n"
    for c in data:
        result += f"{c['customer_id']} - {c['customer_name']}: 授信{c['credit_limit']:,.0f}, 贷款{c['loan_limit']:,.0f}\n"
    return result

def format_list_approvals(data: Any) -> str:
    if not data:
        return "暂无审批数据"
    if isinstance(data, dict) and "error" in data:
        return f"查询失败: {data['error']}"
    status_emoji = {"已通过": "✅", "已拒绝": "❌", "审批中": "⏳"}
    result = "所有客户审批信息：\n\n"
    for a in data:
        emoji = status_emoji.get(a['approval_status'], "📌")
        result += f"{a['customer_id']} - {a['customer_name']}: {a['apply_type']} {a['apply_amount']:,.0f}元 {emoji}{a['approval_status']}\n"
    return result
