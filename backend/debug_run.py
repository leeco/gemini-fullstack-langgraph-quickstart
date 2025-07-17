#!/usr/bin/env python3
"""
快速调试运行脚本
无需传参数，直接运行即可测试
"""
import os
import sys
from pathlib import Path

# 设置工作目录
backend_dir = Path(__file__).parent
os.chdir(backend_dir)

# 添加src到Python路径
src_dir = backend_dir / "src"
sys.path.insert(0, str(src_dir))

# 设置测试用的API Key（如果未设置的话）
if not os.getenv("DASHSCOPE_API_KEY"):
    print("⚠️  未设置真实API Key，使用测试模式")
    os.environ["DASHSCOPE_API_KEY"] = "test-key-for-debugging"

print("🚀 启动调试模式...")
print("=" * 60)

# 导入并运行
try:
    from examples.cli_research import main
    
    # 模拟命令行参数
    sys.argv = ["cli_research.py", "--debug"]
    
    main()
    
except Exception as e:
    print(f"❌ 运行出错: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("🎯 调试完成") 