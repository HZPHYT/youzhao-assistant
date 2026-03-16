import logging
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class RAGQualityChecker:
    def __init__(self, llm_client, min_score=0.5):
        self.llm_client = llm_client
        self.min_score = min_score
    
    def check_relevance(self, query: str, documents: List[str]) -> Dict[str, Any]:
        if not documents:
            return {
                "is_relevant": False,
                "score": 0.0,
                "reason": "无检索结果"
            }
        
        docs_text = "\n\n".join([f"文档{i+1}: {doc[:200]}..." for i, doc in enumerate(documents)])
        
        prompt = f"""请判断检索到的文档是否与用户问题相关。

用户问题：{query}

检索到的文档：
{docs_text}

请以JSON格式返回判断结果：
{{
    "is_relevant": true/false,
    "score": 0.0-1.0,
    "reason": "判断原因"
}}

注意：
- 如果文档内容与问题完全不相关，返回is_relevant: false
- 如果文档内容部分相关，返回is_relevant: true
- score表示相关程度，1.0表示完全相关"""

        try:
            response = self.llm_client.chat.completions.create(
                model="glm-4.6v-flashx",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            result_text = response.choices[0].message.content
            
            import json
            result_text = result_text.strip()
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
            result_text = result_text.strip()
            
            result = json.loads(result_text)
            
            result["is_relevant"] = result.get("is_relevant", False) and result.get("score", 0) >= self.min_score
            
            return result
            
        except Exception as e:
            logger.error(f"质量检查失败: {e}")
            return {
                "is_relevant": False,
                "score": 0.0,
                "reason": f"检查失败: {str(e)}"
            }
    
    def filter_results(self, query: str, documents: List[str], scores: List[float]) -> Dict[str, Any]:
        if not documents:
            return {"documents": [], "scores": [], "quality_check": {"is_relevant": False}}
        
        quality_result = self.check_relevance(query, documents)
        
        filtered_docs = []
        filtered_scores = []
        
        for doc, score in zip(documents, scores):
            if score >= self.min_score:
                filtered_docs.append(doc)
                filtered_scores.append(score)
        
        if not filtered_docs and quality_result["is_relevant"]:
            filtered_docs = documents[:1]
            filtered_scores = scores[:1]
        
        return {
            "documents": [filtered_docs],
            "scores": [filtered_scores],
            "quality_check": quality_result
        }

def create_quality_checker(llm_client):
    return RAGQualityChecker(llm_client, min_score=0.5)
