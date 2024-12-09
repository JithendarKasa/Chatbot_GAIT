import axios from 'axios';

const API_BASE_URL = 'http://localhost:5000/api';

export const chatAPI = {
  sendMessage: async (message) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/chat`, { message });
      return response.data;
    } catch (error) {
      console.error('Chat API Error:', error);
      throw error;
    }
  }
};