# main.py - AI私人厨师主程序
from app.agents.ai_chef import graph as agent
from app.recipe_text import format_recipe_blocks

def main():
  print("=" * 50)
  print("欢迎使用 AI 私人厨师！")
  print("=" * 50)
  print("功能：根据你的食材推荐菜谱")
  print("输入 'quit' 或 'exit' 退出程序")
  print("=" * 50)

  while True:
      # 获取用户输入
      user_input = input("\n请描述你的食材或需求：").strip()

      # 检查退出命令
      if user_input.lower() in ['quit', 'exit', '退出']:
          print("\n感谢使用，再见！")
          break

      # 检查空输入
      if not user_input:
          print("请输入内容！")
          continue

      # 调用 AI 代理
      print("\n正在思考中...\n")
      try:
          response = agent.invoke({
              "messages": [{"role": "user", "content": user_input}]
          })

          # 显示结果（把菜谱 JSON 渲染成可读文本，避免原样打印）
          print("AI 建议：")
          print("-" * 50)
          print(format_recipe_blocks(response["messages"][-1].content, markdown=False))
          print("-" * 50)

      except Exception as e:
          print(f"出错了：{e}")
          print("请检查网络连接和API配置")

if __name__ == "__main__":
  main()