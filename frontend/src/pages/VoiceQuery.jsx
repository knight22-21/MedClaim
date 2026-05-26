import React, { useState, useRef } from 'react';
import { api } from '../api/client';
import { Mic, Send, Volume2, Database, BrainCircuit, Activity } from 'lucide-react';

export default function VoiceQuery() {
  const [queryText, setQueryText] = useState("");
  const [messages, setMessages] = useState([
    { role: 'system', text: "Hello! I am MedClaim's Voice AI. You can ask me about claim statuses, coding guidelines, payer policies, or analytics." }
  ]);
  const [loading, setLoading] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  const playAudio = (base64Audio) => {
    const audio = new Audio(base64Audio);
    audio.play();
  };

  const handleTextSubmit = async (e) => {
    e.preventDefault();
    if (!queryText.trim()) return;

    const userMessage = { role: 'user', text: queryText };
    setMessages(prev => [...prev, userMessage]);
    setQueryText("");
    setLoading(true);

    try {
      const res = await api.submitTextQuery(userMessage.text);
      const data = res.data.data;
      
      const aiMessage = {
        role: 'ai',
        text: data.response_text,
        intent: data.intent,
        sources: data.sources,
        audio: data.audio_base64
      };
      
      setMessages(prev => [...prev, aiMessage]);
      if (data.audio_base64) playAudio(data.audio_base64);
      
    } catch (err) {
      console.error(err);
      setMessages(prev => [...prev, { role: 'ai', text: "Sorry, I encountered an error processing your query." }]);
    } finally {
      setLoading(false);
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) audioChunksRef.current.push(event.data);
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        
        // Optimistically add user placeholder
        setMessages(prev => [...prev, { role: 'user', text: "🎤 [Audio Message]" }]);
        setLoading(true);
        
        try {
          const res = await api.submitVoiceQuery(audioBlob);
          const data = res.data.data;
          
          // Update the placeholder with actual transcription
          setMessages(prev => {
            const newMessages = [...prev];
            newMessages[newMessages.length - 1].text = data.transcription;
            return newMessages;
          });
          
          const aiMessage = {
            role: 'ai',
            text: data.response_text,
            intent: data.intent,
            sources: data.sources,
            audio: data.audio_base64
          };
          
          setMessages(prev => [...prev, aiMessage]);
          if (data.audio_base64) playAudio(data.audio_base64);
          
        } catch (err) {
          console.error(err);
          setMessages(prev => [...prev, { role: 'ai', text: "Sorry, I encountered an error processing your voice query." }]);
        } finally {
          setLoading(false);
        }
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (err) {
      console.error("Microphone access denied", err);
      alert("Microphone access is required for voice queries.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach(t => t.stop());
      setIsRecording(false);
    }
  };

  return (
    <div className="flex-col gap-6 animate-fade-in" style={{ height: 'calc(100vh - 140px)' }}>
      <div>
        <h1>Voice AI Assistant</h1>
        <p style={{ color: 'var(--text-secondary)' }}>Interact with MedClaim via voice or text.</p>
      </div>

      <div className="glass-card" style={{ flex: 1, display: 'flex', flexDirection: 'column', padding: 0, overflow: 'hidden' }}>
        
        {/* Chat History */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '24px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {messages.map((msg, i) => (
            <div key={i} style={{ display: 'flex', justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
              <div style={{ 
                maxWidth: '70%', 
                background: msg.role === 'user' ? 'var(--primary)' : 'var(--bg-surface)', 
                border: msg.role === 'user' ? 'none' : '1px solid var(--border-glass)',
                padding: '16px', 
                borderRadius: '16px',
                borderBottomRightRadius: msg.role === 'user' ? 0 : '16px',
                color: msg.role === 'user' ? '#fff' : 'inherit',
              }}>
                <div style={{ whiteSpace: 'pre-wrap' }}>{msg.text}</div>
                
                {msg.role === 'ai' && msg.intent && (
                  <div style={{ marginTop: '16px', display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    <span className="badge" style={{ background: 'rgba(59, 130, 246, 0.1)', color: 'var(--primary)', display: 'flex', gap: '4px', alignItems: 'center' }}>
                      <BrainCircuit size={12}/> {msg.intent}
                    </span>
                    {msg.sources && msg.sources.map((src, idx) => (
                      <span key={idx} className="badge" style={{ background: 'rgba(16, 185, 129, 0.1)', color: 'var(--success)', display: 'flex', gap: '4px', alignItems: 'center' }}>
                        <Database size={12}/> {src}
                      </span>
                    ))}
                    {msg.audio && (
                      <button onClick={() => playAudio(msg.audio)} style={{ background: 'none', border: 'none', color: 'var(--info)', cursor: 'pointer', display: 'flex', alignItems: 'center' }}>
                        <Volume2 size={16} />
                      </button>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
          
          {loading && (
            <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
              <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-glass)', padding: '16px', borderRadius: '16px' }}>
                <Activity className="animate-pulse" size={20} color="var(--primary)" />
              </div>
            </div>
          )}
        </div>

        {/* Input Area */}
        <div style={{ borderTop: '1px solid var(--border-glass)', padding: '16px 24px', background: 'rgba(0,0,0,0.2)' }}>
          <form onSubmit={handleTextSubmit} style={{ display: 'flex', gap: '12px' }}>
            <button 
              type="button"
              className={`btn ${isRecording ? 'btn-danger' : 'btn-glass'}`} 
              onClick={isRecording ? stopRecording : startRecording}
              style={{ borderRadius: '50%', width: '48px', height: '48px', padding: 0, background: isRecording ? 'var(--danger)' : 'var(--bg-surface)' }}
            >
              {isRecording ? <Activity className="animate-pulse" size={20} /> : <Mic size={20} />}
            </button>
            <input 
              type="text" 
              value={queryText}
              onChange={(e) => setQueryText(e.target.value)}
              placeholder="Type your query or use the microphone..." 
              style={{ flex: 1, background: 'var(--bg-surface)', border: '1px solid var(--border-glass)', borderRadius: '24px', padding: '0 20px', color: 'var(--text-primary)', outline: 'none' }}
              disabled={loading || isRecording}
            />
            <button type="submit" className="btn btn-primary" style={{ borderRadius: '50%', width: '48px', height: '48px', padding: 0 }} disabled={loading || !queryText.trim()}>
              <Send size={18} />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
