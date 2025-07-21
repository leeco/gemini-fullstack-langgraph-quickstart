import os
import logging
import numpy as np
from typing import List, Dict, Any, Optional
from pymilvus import MilvusClient, connections
from dashscope import TextEmbedding

# 配置常量
DEFAULT_MODEL = "text-embedding-v3"
DEFAULT_EMBEDDING_DIM = 1024
DEFAULT_COLLECTION = "demo"

# 默认Milvus配置
DEFAULT_MILVUS_CONFIG = {
    "uri": "https://in03-919fce174d14974.serverless.gcp-us-west1.cloud.zilliz.com",
    "token": "ae08f8ea65f4b78fab644620cc7b993f727bc1d28cd5711920d702fd41d0b277f44c560a3804bbb23d709b017e51919ac461d522"
}

# 配置日志
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class NativeMilvusSyncEngine:
    """原生PyMilvus同步查询引擎 - 完全同步，无异步依赖"""
    
    def __init__(self, collection_name: str = DEFAULT_COLLECTION):
        self.collection_name = collection_name
        self.api_key = self._get_api_key()
        self._client: Optional[MilvusClient] = None
        logger.info(f"初始化原生同步查询引擎: {collection_name}")
    
    def _get_api_key(self) -> str:
        api_key = os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            raise ValueError("环境变量 DASHSCOPE_API_KEY 未设置")
        return api_key
    
    def _ensure_connected(self):
        """确保客户端连接"""
        if self._client is None:
            self._connect()
    
    def _connect(self):
        """建立同步连接"""
        try:
            self._client = MilvusClient(
                uri=os.getenv("MILVUS_URI", DEFAULT_MILVUS_CONFIG["uri"]),
                token=os.getenv("MILVUS_TOKEN", DEFAULT_MILVUS_CONFIG["token"])
            )
            # 检查集合是否存在
            if not self._client.has_collection(self.collection_name):
                logger.warning(f"集合 {self.collection_name} 不存在")
            else:
                logger.info(f"成功连接到Milvus集合: {self.collection_name}")
        except Exception as e:
            logger.error(f"Milvus连接失败: {e}")
            raise
    
    def _get_embedding(self, text: str) -> List[float]:
        """获取文本嵌入向量"""
        try:
            response = TextEmbedding.call(
                model=DEFAULT_MODEL,
                input=text,
                api_key=self.api_key
            )
            
            if response.status_code == 200:
                embeddings = response.output['embeddings']
                if embeddings and len(embeddings) > 0:
                    return embeddings[0]['embedding']
            
            raise ValueError(f"获取嵌入向量失败: {response}")
            
        except Exception as e:
            logger.error(f"嵌入向量生成失败: {e}")
            raise
    
    def query(self, text: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """同步查询向量数据库"""
        if not text or not text.strip():
            raise ValueError("查询文本不能为空")
        
        text = text.strip()
        logger.info(f"原生同步查询: '{text}' (top_k={top_k})")
        
        self._ensure_connected()
        
        try:
            # 1. 获取查询向量
            query_vector = self._get_embedding(text)
            
            # 2. 执行向量搜索
            search_results = self._client.search(
                collection_name=self.collection_name,
                data=[query_vector],
                anns_field="embedding",  # 向量字段名
                limit=top_k,
                output_fields=["*"]  # 返回所有字段
            )
            
            if not search_results or not search_results[0]:
                logger.warning("未找到匹配结果")
                return []
            
            # 3. 格式化结果
            results = []
            for i, hit in enumerate(search_results[0]):
                formatted_result = self._format_result(hit, i)
                results.append(formatted_result)
            
            logger.info(f"查询完成，返回{len(results)}个结果")
            return results
            
        except Exception as e:
            logger.error(f"原生同步查询失败: {e}")
            raise
    
    def _format_result(self, hit, index: int) -> Dict[str, Any]:
        """格式化单个查询结果"""
        entity = hit.get('entity', {})
        
        # 提取元数据
        file_name = entity.get('file_name', f'Document_{index}')
        text_content = entity.get('text', '')
        doc_id = entity.get('doc_id', f'doc_{index}')
        
        return {
            "source": "milvus",
            "title": file_name,
            "url": f"internal://doc_{doc_id}",
            "snippet": text_content[:200] + "..." if len(text_content) > 200 else text_content,
            "summary": text_content,
            "score": float(hit.get('distance', 0.0)),  # 注意：distance越小表示越相似
            "metadata": {
                "doc_id": doc_id,
                "file_name": file_name,
                "distance": hit.get('distance', 0.0)
            }
        }
    
    def close(self):
        """关闭连接"""
        if self._client:
            self._client.close()
            self._client = None


# 全局引擎实例（单例模式）
_global_engine = None

def get_engine(collection_name: str = DEFAULT_COLLECTION) -> NativeMilvusSyncEngine:
    """获取全局引擎实例"""
    global _global_engine
    if _global_engine is None or _global_engine.collection_name != collection_name:
        _global_engine = NativeMilvusSyncEngine(collection_name)
    return _global_engine


# 便捷同步查询函数
def query_sync(text: str, top_k: int = 3, collection: str = DEFAULT_COLLECTION) -> List[Dict[str, Any]]:
    """完全同步的查询接口 - 推荐使用"""
    engine = get_engine(collection)
    return engine.query(text, top_k)


def query(text: str, top_k: int = 3, collection: str = DEFAULT_COLLECTION) -> List[Dict[str, Any]]:
    """同步查询接口"""
    return query_sync(text, top_k, collection)


def doc_search(query_text: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """文档搜索接口"""
    return query_sync(query_text, top_k)


# 保留异步接口以兼容（实际使用同步实现）
async def query_async(text: str, top_k: int = 3, collection: str = DEFAULT_COLLECTION) -> List[Dict[str, Any]]:
    """异步查询接口（内部使用同步实现）"""
    return query_sync(text, top_k, collection)


if __name__ == "__main__":
    def test():
        try:
            print("测试原生Milvus同步查询...")
            results = query_sync("测试查询", top_k=2)
            print(f"找到 {len(results)} 个结果")
            for i, result in enumerate(results):
                print(f"{i+1}. {result['title']} (score: {result['score']:.3f})")
        except Exception as e:
            logger.error(f"测试失败: {e}")
    
    test()