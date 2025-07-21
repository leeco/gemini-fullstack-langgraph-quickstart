import os
import logging
import json
import asyncio
from typing import List, Dict, Any

from llama_index.core import VectorStoreIndex, Settings
from llama_index.vector_stores.milvus import MilvusVectorStore
from llama_index.embeddings.dashscope import DashScopeEmbedding

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


class MilvusQueryEngine:
    """简洁的Milvus向量查询引擎"""
    
    def __init__(self, collection_name: str = DEFAULT_COLLECTION):
        """初始化查询引擎
        
        Args:
            collection_name: Milvus集合名称
        """
        self.collection_name = collection_name
        self.api_key = self._get_api_key()
        self._vector_store = None
        self._index = None
        
        # 设置embedding模型
        Settings.embed_model = DashScopeEmbedding(
            model_name=DEFAULT_MODEL,
            api_key=self.api_key,
            dimensions=DEFAULT_EMBEDDING_DIM
        )
        logger.info(f"初始化查询引擎: {collection_name}")
    
    def _get_api_key(self) -> str:
        """获取API密钥"""
        api_key = os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            raise ValueError("环境变量 DASHSCOPE_API_KEY 未设置")
        return api_key
    
    async def _ensure_connected(self):
        """确保连接已建立"""
        if self._vector_store is None:
            await self._connect()
    
    async def _connect(self):
        """连接到Milvus"""
        try:
            self._vector_store = MilvusVectorStore(
                uri=os.getenv("MILVUS_URI", DEFAULT_MILVUS_CONFIG["uri"]),
                token=os.getenv("MILVUS_TOKEN", DEFAULT_MILVUS_CONFIG["token"]),
                collection_name=self.collection_name,
                dim=DEFAULT_EMBEDDING_DIM,
                overwrite=False,
                store_metadata=True
            )
            self._index = VectorStoreIndex.from_vector_store(self._vector_store)
            logger.info("Milvus连接成功")
        except Exception as e:
            logger.error(f"Milvus连接失败: {e}")
            raise
    
    async def query(self, text: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """查询向量数据库
        
        Args:
            text: 查询文本
            top_k: 返回结果数量
            
        Returns:
            标准格式的查询结果
        """
        if not text or not text.strip():
            raise ValueError("查询文本不能为空")
        
        text = text.strip()
        logger.info(f"查询: '{text}' (top_k={top_k})")
        
        await self._ensure_connected()
        
        try:
            # 执行查询
            retriever = self._index.as_retriever(similarity_top_k=top_k)
            results = await retriever.aretrieve(text)
            
            if not results:
                logger.warning("未找到匹配结果")
                return []
            
            # 格式化结果
            return [self._format_result(result, i) for i, result in enumerate(results)]
            
        except Exception as e:
            logger.error(f"查询失败: {e}")
            raise
    
    def _format_result(self, result, index: int) -> Dict[str, Any]:
        """格式化单个查询结果"""
        node = result.node
        metadata = getattr(node, 'metadata', {})
        text = getattr(node, 'text', '')
        
        return {
            "source": "milvus",
            "title": metadata.get("file_name", f"Document_{index}"),
            "url": f"internal://doc_{metadata.get('doc_id', index)}",
            "snippet": text[:200] + "..." if len(text) > 200 else text,
            "summary": text,
            "score": getattr(result, 'score', 0.0),
            "metadata": {
                "node_id": getattr(node, 'id_', 'unknown'),
                "node_index": metadata.get("node_index"),
                "doc_id": metadata.get("doc_id"),
                "file_name": metadata.get("file_name")
            }
        }


# 便捷查询函数
async def query_async(text: str, top_k: int = 3, collection: str = DEFAULT_COLLECTION) -> List[Dict[str, Any]]:
    """异步查询接口"""
    engine = MilvusQueryEngine(collection)
    return await engine.query(text, top_k)


def query(text: str, top_k: int = 3, collection: str = DEFAULT_COLLECTION) -> List[Dict[str, Any]]:
    """同步查询接口"""
    try:
        import nest_asyncio
        nest_asyncio.apply()
        return asyncio.run(query_async(text, top_k, collection))
    except Exception as e:
        logger.error(f"查询失败: {e}")
        raise


# 向后兼容接口
def query_documents(query_text: str, top_k: int = 3, collection_name: str = DEFAULT_COLLECTION) -> List[Dict[str, Any]]:
    """查询文档接口（向后兼容）"""
    return query(query_text, top_k, collection_name)


async def query_documents_async(query_text: str, top_k: int = 3, collection_name: str = DEFAULT_COLLECTION) -> List[Dict[str, Any]]:
    """异步查询文档接口（向后兼容）"""
    return await query_async(query_text, top_k, collection_name)


def doc_search(query_text: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """文档搜索接口（向后兼容）"""
    return query(query_text, top_k)


if __name__ == "__main__":
    async def test():
        """测试函数"""
        try:
            results = await query_async("测试查询", top_k=2)
            print(json.dumps(results, indent=2, ensure_ascii=False))
        except Exception as e:
            logger.error(f"测试失败: {e}")
    
    asyncio.run(test())