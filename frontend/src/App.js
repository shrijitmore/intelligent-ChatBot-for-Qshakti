import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Send, Sparkles, RotateCcw, MessageCircle } from 'lucide-react';
import '@/App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [treePath, setTreePath] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isInitializing, setIsInitializing] = useState(true);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    initializeChat();
  }, []);

  const initializeChat = async () => {
    try {
      setIsInitializing(true);
      const response = await axios.post(`${API}/chat/initialize`, {});
      setSessionId(response.data.session_id);
      setSuggestions(response.data.suggestions);
      setMessages([{
        role: 'assistant',
        content: 'Welcome! I\'m your intelligent data assistant. I can help you explore and understand your Quality Control and Manufacturing Management database. Here are some suggestions to get started:',
        timestamp: new Date().toISOString()
      }]);
    } catch (error) {
      console.error('Error initializing chat:', error);
    } finally {
      setIsInitializing(false);
    }
  };

  const sendMessage = async (message, isSuggestion = false) => {
    if (!message.trim() || !sessionId) return;

    const userMessage = {
      role: 'user',
      content: message,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      const response = await axios.post(`${API}/chat/message`, {
        session_id: sessionId,
        message: message,
        is_suggestion: isSuggestion
      });

      const assistantMessage = {
        role: 'assistant',
        content: response.data.response,
        timestamp: new Date().toISOString(),
        metadata: response.data.metadata
      };

      setMessages(prev => [...prev, assistantMessage]);
      setSuggestions(response.data.suggestions);
      setTreePath(response.data.context_path);
    } catch (error) {
      console.error('Error sending message:', error);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date().toISOString(),
        isError: true
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSuggestionClick = (suggestion) => {
    sendMessage(suggestion, true);
  };

  const handleReset = () => {
    initializeChat();
    setMessages([]);
    setTreePath([]);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (inputValue.trim()) {
      sendMessage(inputValue, false);
    }
  };

  if (isInitializing) {
    return (
      <div className="app-container">
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p className="loading-text">Initializing chatbot...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="header-content">
          <div className="header-left">
            <MessageCircle className="header-icon" />
            <div>
              <h1 className="header-title">Data Intelligence Bot</h1>
              <p className="header-subtitle">Explore your database with AI</p>
            </div>
          </div>
          <button 
            onClick={handleReset} 
            className="reset-button"
            data-testid="reset-button"
          >
            <RotateCcw size={18} />
            <span>New Chat</span>
          </button>
        </div>
      </header>

      {/* Decision Tree Breadcrumb */}
      {treePath.length > 0 && (
        <div className="tree-path-container">
          <div className="tree-path">
            <span className="tree-path-label">Conversation Path:</span>
            {treePath.map((item, index) => (
              <React.Fragment key={index}>
                <span className="tree-path-item">{item}</span>
                {index < treePath.length - 1 && (
                  <span className="tree-path-arrow">→</span>
                )}
              </React.Fragment>
            ))}
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="main-content">
        {/* Messages */}
        <div className="messages-container" data-testid="messages-container">
          {messages.map((msg, index) => (
            <div 
              key={index} 
              className={`message ${msg.role}`}
              data-testid={`message-${msg.role}`}
            >
              <div className="message-content">
                {msg.role === 'assistant' && (
                  <div className="message-avatar assistant-avatar">
                    <Sparkles size={16} />
                  </div>
                )}
                <div className="message-bubble">
                  <p>{msg.content}</p>
                  {msg.metadata?.relevant_tables && (
                    <div className="message-metadata">
                      <small>Relevant tables: {msg.metadata.relevant_tables.join(', ')}</small>
                    </div>
                  )}
                </div>
                {msg.role === 'user' && (
                  <div className="message-avatar user-avatar">You</div>
                )}
              </div>
            </div>
          ))}
          
          {isLoading && (
            <div className="message assistant" data-testid="loading-indicator">
              <div className="message-content">
                <div className="message-avatar assistant-avatar">
                  <Sparkles size={16} />
                </div>
                <div className="message-bubble loading-bubble">
                  <div className="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        {/* Suggestions */}
        {suggestions.length > 0 && !isLoading && (
          <div className="suggestions-container">
            <p className="suggestions-title">Suggested explorations:</p>
            <div className="suggestions-grid">
              {suggestions.map((suggestion, index) => (
                <button
                  key={index}
                  onClick={() => handleSuggestionClick(suggestion)}
                  className="suggestion-card"
                  data-testid={`suggestion-${index}`}
                >
                  <Sparkles size={14} className="suggestion-icon" />
                  <span>{suggestion}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Input Area */}
        <div className="input-container">
          <form onSubmit={handleSubmit} className="input-form">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Type your question or select a suggestion above..."
              className="input-field"
              disabled={isLoading}
              data-testid="message-input"
            />
            <button 
              type="submit" 
              className="send-button" 
              disabled={isLoading || !inputValue.trim()}
              data-testid="send-button"
            >
              <Send size={20} />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

export default App;
