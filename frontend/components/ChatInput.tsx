"use client";

import { useRef, useState } from "react";

interface Props {
  onSend: (message: string) => void;
  disabled: boolean;
}

export default function ChatInput({ onSend, disabled }: Props) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  function submit() {
    const msg = value.trim();
    if (!msg || disabled) return;
    onSend(msg);
    setValue("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }

  function handleInput(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setValue(e.target.value);
    // Auto-grow up to 4 rows
    const el = e.target;
    el.style.height = "auto";
    const lineHeight = 20;
    el.style.height = `${Math.min(el.scrollHeight, lineHeight * 4)}px`;
  }

  return (
    <div className="flex items-end gap-3">
      <textarea
        ref={textareaRef}
        rows={1}
        value={value}
        onChange={handleInput}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        placeholder={disabled ? "Thinking…" : "Ask a question about your documents"}
        className="min-w-0 flex-1 resize-none overflow-hidden rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-500 focus:ring-1 focus:ring-slate-500 disabled:opacity-50"
      />
      <button
        onClick={submit}
        disabled={disabled || !value.trim()}
        className="shrink-0 rounded-md bg-slate-950 px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
      >
        Send
      </button>
    </div>
  );
}
