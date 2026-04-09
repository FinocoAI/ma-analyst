"use client";
import { useState, useCallback, useEffect } from "react";
import { ChatMessage } from "@/lib/types";
import { streamChatMessage, getChatHistory } from "@/lib/api";

const generateUUID = () => {
  if (typeof window !== "undefined" && window.crypto && window.crypto.randomUUID) {
    return window.crypto.randomUUID();
  }
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
};

export function useChat(runId: string | null) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!runId) {
      setMessages([]);
      return;
    }
    
    // Fetch history
    const fetchHistory = async () => {
      try {
        const { messages: history } = await getChatHistory(runId);
        setMessages(history);
      } catch (e) {
        console.error("Failed to load chat history:", e);
      }
    };
    fetchHistory();
  }, [runId]);

  const sendMessage = useCallback(async (content: string) => {
    if (!runId || !content.trim()) return;

    const userMsg: ChatMessage = {
      id: generateUUID(),
      run_id: runId,
      role: "user",
      content,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    const assistantMsgId = generateUUID();
    const assistantMsg: ChatMessage = {
      id: assistantMsgId,
      run_id: runId,
      role: "assistant",
      content: "",
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, assistantMsg]);

    try {
      const res = await streamChatMessage(runId, content);
      const reader = res.body?.getReader();
      const decoder = new TextDecoder();

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value);
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantMsgId ? { ...m, content: m.content + chunk } : m
            )
          );
        }
      }
    } catch (e: any) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantMsgId
            ? { ...m, content: "Error: " + e.message }
            : m
        )
      );
    } finally {
      setIsLoading(false);
    }
  }, [runId]);

  return { messages, isLoading, sendMessage };
}
