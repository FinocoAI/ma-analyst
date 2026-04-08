import { ChatMessage as ChatMsg } from "@/lib/types";

export function ChatMessage({ message }: { message: ChatMsg }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-xl px-3 py-2 text-sm ${
          isUser
            ? "bg-stone-800 text-white"
            : "bg-gray-100 text-gray-800"
        }`}
      >
        {isUser ? (
          <p>{message.content}</p>
        ) : (
          <div className="whitespace-pre-wrap leading-relaxed">{message.content}</div>
        )}
      </div>
    </div>
  );
}
