import React, { useState, useRef, useEffect } from "react";

const ChatContainer = () => {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isGeneratingImage, setIsGeneratingImage] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!inputMessage.trim() || isLoading) return;

    try {
      setIsLoading(true);
      const userMessage = {
        type: "user",
        content: inputMessage,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMessage]);
      setInputMessage("");

      const response = await fetch("http://127.0.0.1:5000/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: inputMessage,
          audio_requested: true,
        }),
      });

      const data = await response.json();
      console.log("Response data:", data); // Debug log

      if (!response.ok) {
        throw new Error(data.error || "Failed to get response");
      }

      const assistantMessage = {
        type: "assistant",
        content: data.message,
        sources: data.sources,
        used_context: data.used_context,
        context_preview: data.context_preview,
        is_course_related: data.is_course_related,
        audio: data.audio,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error("Chat error:", error);
      const errorMessage = {
        type: "error",
        content: "Sorry, there was an error processing your request.",
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleImageGeneration = async (prompt) => {
    try {
      setIsGeneratingImage(true);
      const userMessage = {
        type: "user",
        content: `Generated image for prompt: "${prompt}"`,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMessage]);
      setInputMessage("");

      const response = await fetch("http://127.0.0.1:5000/api/generate-image", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ prompt }),
      });

      const data = await response.json();
      if (data.success && data.image) {
        const assistantMessage = {
          type: "assistant",
          content: `Here's an anatomical illustration based on your request. This image shows ${prompt}. The illustration includes detailed labeling and anatomical structures commonly used in medical education.`,
          image: data.image,
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, assistantMessage]);
      }
    } catch (error) {
      console.error("Error generating image:", error);
      const errorMessage = {
        type: "error",
        content: "Sorry, there was an error generating the image.",
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsGeneratingImage(false);
    }
  };

  const MessageContent = ({ message }) => {
    const [isPlaying, setIsPlaying] = useState(false);
    const [showResume, setShowResume] = useState(false);
    const audioRef = useRef(null);

    const toggleAudio = (audioBase64) => {
      if (!audioBase64) {
        console.log("No audio data available");
        return;
      }

      try {
        if (!audioRef.current) {
          audioRef.current = new Audio(`data:audio/mp3;base64,${audioBase64}`);

          // Add event listeners
          audioRef.current.addEventListener("ended", () => {
            setIsPlaying(false);
            setShowResume(false);
          });

          audioRef.current.addEventListener("error", (error) => {
            console.error("Error playing audio:", error);
            setIsPlaying(false);
            setShowResume(false);
          });
        }

        if (isPlaying) {
          audioRef.current.pause();
          setIsPlaying(false);
          setShowResume(true);
        } else {
          audioRef.current.play();
          setIsPlaying(true);
          setShowResume(false);
        }
      } catch (error) {
        console.error("Error handling audio:", error);
        setIsPlaying(false);
        setShowResume(false);
      }
    };

    const restartAudio = () => {
      if (audioRef.current) {
        audioRef.current.currentTime = 0;
        audioRef.current.play();
        setIsPlaying(true);
        setShowResume(false);
      }
    };

    // Cleanup audio on unmount
    useEffect(() => {
      return () => {
        if (audioRef.current) {
          audioRef.current.pause();
          audioRef.current = null;
        }
      };
    }, []);

    return (
      <div>
        <p className="text-sm mb-2">{message.content}</p>
        {message.type === "assistant" && (
          <div className="mt-2 space-y-2">
            {message.used_context && message.is_course_related && (
              <div className="flex flex-col gap-2">
                {message.sources && (
                  <p className="text-xs text-gray-600">
                    📚 Source: {message.sources.filename}
                  </p>
                )}
                {message.context_preview && (
                  <details className="text-xs">
                    <summary className="cursor-pointer text-blue-600 hover:text-blue-700">
                      View Reference Context
                    </summary>
                    <div className="mt-2 p-2 bg-gray-50 rounded text-gray-700">
                      {message.context_preview}...
                    </div>
                  </details>
                )}
              </div>
            )}
            {message.image && (
              <div className="mt-2">
                <img
                  src={`data:image/png;base64,${message.image}`}
                  alt="Generated illustration"
                  className="rounded-lg max-w-full"
                />
              </div>
            )}
            {message.audio && (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => toggleAudio(message.audio)}
                  className="px-3 py-1 bg-blue-500 text-white rounded-md text-xs hover:bg-blue-600 flex items-center gap-2"
                >
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    className="h-4 w-4"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    {isPlaying ? (
                      // Pause icon
                      <path
                        fillRule="evenodd"
                        d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z"
                        clipRule="evenodd"
                      />
                    ) : (
                      // Play/Resume icon
                      <path
                        fillRule="evenodd"
                        d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z"
                        clipRule="evenodd"
                      />
                    )}
                  </svg>
                  {isPlaying ? "Stop" : showResume ? "Resume" : "Listen to Response"}
                </button>
                {showResume && (
                  <button
                    onClick={restartAudio}
                    className="px-3 py-1 bg-green-500 text-white rounded-md text-xs hover:bg-green-600"
                  >
                    Start Over
                  </button>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="flex flex-col h-[90vh] max-w-5xl mx-auto bg-white rounded-lg shadow-lg">
      <div className="p-4 border-b">
        <h1 className="text-xl font-semibold">PTRS:6224 Course Assistant</h1>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message, index) => (
          <div
            key={index}
            className={`flex ${
              message.type === "user" ? "justify-end" : "justify-start"
            }`}
          >
            <div
              className={`max-w-[80%] rounded-lg p-3 ${
                message.type === "user"
                  ? "bg-blue-500 text-white"
                  : message.type === "error"
                  ? "bg-red-100 text-red-700"
                  : "bg-gray-100 text-gray-900"
              }`}
            >
              <MessageContent message={message} />
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSubmit} className="p-4 border-t">
        <div className="flex gap-2">
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            placeholder="Ask a question about the course..."
            disabled={isLoading || isGeneratingImage}
            className="flex-1 p-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            type="button"
            onClick={() => handleImageGeneration(inputMessage)}
            disabled={isLoading || isGeneratingImage || !inputMessage.trim()}
            className="px-4 py-2 bg-green-500 text-white rounded-lg disabled:opacity-50 hover:bg-green-600 transition-colors"
          >
            {isGeneratingImage ? "Generating..." : "Generate Image"}
          </button>
          <button
            type="submit"
            disabled={isLoading || isGeneratingImage || !inputMessage.trim()}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg disabled:opacity-50 hover:bg-blue-600 transition-colors"
          >
            {isLoading ? "Sending..." : "Send"}
          </button>
        </div>
      </form>
    </div>
  );
};

export default ChatContainer;
