import json
import random
import time
from locust import HttpUser, task, between

class RAGSystemUser(HttpUser):
    wait_time = between(2, 5)
    
    def on_start(self):
        """Initialize test data when user starts"""
        # Test queries for your RAG system
        self.test_queries = [
            "How to install MetaMask?",
            "What is MetaMask wallet?",
            "How to connect to DeFi applications?",
            "How to send cryptocurrency?",
            "What are gas fees?",
            "How to add custom tokens?",
            "How to backup wallet?",
            "How to restore wallet from seed phrase?",
            "What networks does MetaMask support?",
            "How to swap tokens?",
            "How to connect hardware wallet?",
            "What is a seed phrase?",
            "How to secure my wallet?",
            "How to import account?",
            "How to use browser extension?",
        ]
    
    @task(4)  # Weight: 3 (most common)
    def query_rag_system(self):
        """Test the main query endpoint"""
        query = random.choice(self.test_queries)
        
        payload = {
            "query": query,
            "max_results": 3,
            "temperature": 0.7
        }
        
        with self.client.post(
            "/query",
            json=payload,
            headers={"Content-Type": "application/json"},
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response_data = response.json()
                if "answer" in response_data and response_data["answer"]:
                    response.success()
                else:
                    response.failure("Empty answer received")
            else:
                response.failure(f"Request failed with status {response.status_code}")
    
    @task(1)  # Weight: 1 (less common)
    def health_check(self):
        """Test health endpoint"""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed with status {response.status_code}")
    
    # @task(1)  # Weight: 1 (less common)
    # def api_info(self):
    #     """Test info endpoint"""
    #     with self.client.get("/info", catch_response=True) as response:
    #         if response.status_code == 200:
    #             response.success()
    #         else:
    #             response.failure(f"Info request failed with status {response.status_code}")


class RAGStressUser(HttpUser):
    """Stress testing user with higher load"""
    wait_time = between(1, 3)  # Shorter wait time for stress testing
    
    def on_start(self):
        self.test_queries = [
            "How to install MetaMask?",
            "What is MetaMask wallet?",
            "How to connect to DeFi applications?",
            "How to send cryptocurrency?",
            "What are gas fees?",
        ]
    
    @task
    def rapid_queries(self):
        """Rapid-fire queries for stress testing"""
        query = random.choice(self.test_queries)
        
        payload = {
            "query": query,
            "max_results": 3,
            "temperature": 0.7
        }
        
        self.client.post("/query", json=payload)


# locust -f test.py RAGSystemUser --host=http://45.81.35.238:8001/ --users 3 --spawn-rate 1 --run-time 1m --headless --csv=rag_system_user_test_final