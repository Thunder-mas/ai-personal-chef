import { MessageList } from '../Chat/MessageList'
import { InputArea } from '../Chat/InputArea'

export function MainArea() {
  return (
    <div className="flex-1 flex flex-col min-w-0 h-full">
      <MessageList />
      <InputArea />
    </div>
  )
}
