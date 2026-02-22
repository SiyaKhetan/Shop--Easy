import React, { useState, useEffect, useRef } from 'react';
import './chatbot.css';

// Vite requires the VITE_ prefix to expose variables to the client
const GEMINI_API_KEY = import.meta.env.VITE_GEMINI_API_KEY;

const Chatbot: React.FC = () => {
  const [messages, setMessages] = useState<{text: string, isUser: boolean}[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const getGeminiResponse = async (userInput: string) => {
    // If this triggers, your .env is in the wrong place or you didn't restart npm
    if (!GEMINI_API_KEY) return "DEBUG: API Key undefined. Check .env placement and restart terminal.";

    setIsLoading(true);
    try {
      // FIX: Using /v1/ and the stable model identifier for 2026
      const url = `https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key=${GEMINI_API_KEY}`;
      
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contents: [{ parts: [{ text: userInput }] }]
        })
      });

      const data = await response.json();

      if (data.error) {
        console.error("API Error Code:", data.error.code); // Log for debugging
        return `API Error: ${data.error.message}`;
      }

      return data.candidates[0].content.parts[0].text;
    } catch (error) {
      return "Network error. Please check your internet connection.";
    } finally {
      setIsLoading(false);
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;
    const userMsg = input;
    setMessages(prev => [...prev, { text: userMsg, isUser: true }]);
    setInput('');

    const botResponse = await getGeminiResponse(userMsg);
    setMessages(prev => [...prev, { text: botResponse, isUser: false }]);
  };

  return (
    <div className="chat-container">
      <div className="chat-widget">
        <div className="chat-header">🛒 Shop--Easy Assistant</div>
        <div className="messages">
          {messages.map((msg, i) => (
            <div key={i} className={`message ${msg.isUser ? 'user' : 'bot'}`}>{msg.text}</div>
          ))}
          {isLoading && <div className="message bot">Thinking...</div>}
          <div ref={messagesEndRef} />
        </div>
        <div className="chat-input">
          <input 
            value={input} 
            onChange={(e) => setInput(e.target.value)} 
            onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
            placeholder="Ask about product prices..."
          />
          <button onClick={sendMessage} disabled={isLoading}>Send</button>
        </div>
      </div>
    </div>
  );
};

export default Chatbot;