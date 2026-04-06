"use client";
import { useEffect, useRef } from "react";
import { useChat } from "@/hooks/useChat";
import { ChatMessage } from "./ChatMessage";
import { ChatInput } from "./ChatInput";

interface Props {
  runId: string | null;
  isReady: boolean;
}

export function ChatPanel({ runId, isReady }: Props) {
  const { messages, isLoading, sendMessage } = useChat(runId);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (!isReady) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-center p-6">
        <p className="text-sm text-gray-400">
          Chat will be available once analysis is complete.
        </p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <div className="px-4 py-3 border-b border-gray-200">
        <h3 className="text-sm font-semibold text-gray-700">M&A Assistant</h3>
        <p className="text-xs text-gray-400">Ask about any company, signal, or ranking</p>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
        {messages.length === 0 && (
          <div className="space-y-2">
            {[
              "Why is the top company ranked #1?",
              "Which companies have the strongest acquisition signals?",
              "Compare the top 2 buyers",
            ].map((suggestion) => (
              <button
                key={suggestion}
                onClick={() => sendMessage(suggestion)}
                className="w-full text-left text-xs text-gray-500 bg-gray-50 hover:bg-gray-100 border border-gray-200 rounded-lg px-3 py-2"
              >
                {suggestion}
              </button>
            ))}
          </div>
        )}

        {messages.map((msg) => (
          <ChatMessage key={msg.id} message={msg} />
        ))}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-xl px-3 py-2 text-sm text-gray-400 animate-pulse">
              Thinking...
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="px-4 pb-4">
        <ChatInput onSend={sendMessage} disabled={isLoading} />
      </div>
    </div>
  );
}
