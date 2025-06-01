import requests
import json
import logging
import argparse
from typing import List, Dict, Any, Set
import time
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("recall_evaluation.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("recall_evaluator")

class RecallEvaluator:
    """Class for evaluating Recall@k metric for RAG systems."""
    
    def __init__(self, api_base_url: str, k: int = 3):
        self.api_base_url = api_base_url
        self.endpoint = f"{api_base_url}/query"
        self.session = requests.Session()
        self.k = k
        logger.info(f"Initialized evaluator with parameter k={k}")
        
    def load_assessment_data(self, assessment_file: str) -> Dict[str, Any]:
        """
        Load data from assessment.json file.
        
        Args:
            assessment_file: Path to assessment.json file
            
        Returns:
            Dictionary with assessment data
        """
        try:
            with open(assessment_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"Loaded assessment file: {len(data)} records")
            return data
        except Exception as e:
            logger.error(f"Error loading assessment file: {e}")
            raise
            
    def query_api(self, question: str, max_results: int = None, temperature: float = 0.7) -> Dict[str, Any]:
        """
        Send query to RAG system API.
        
        Args:
            question: Question text
            max_results: Maximum number of results (defaults to k)
            temperature: Temperature for generation
            
        Returns:
            API response with chunk_ids
        """
        if max_results is None:
            max_results = self.k
            
        payload = {
            "query": question,
            "max_results": max_results,
            "temperature": temperature
        }
        
        try:
            response = self.session.post(self.endpoint, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API query error for question '{question}': {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Server response: {e.response.text}")
            return {"error": str(e)}
            
    def calculate_recall_at_k(self, relevant_chunks: List[str], retrieved_chunks: List[str], k: int = None) -> float:
        """
        Calculate Recall@k metric.
        
        Args:
            relevant_chunks: List of relevant chunk_ids from assessment
            retrieved_chunks: List of chunk_ids returned by the system
            k: Number of top results to evaluate (defaults to self.k)
            
        Returns:
            Recall@k value from 0 to 1
        """
        if k is None:
            k = self.k
            
        if not relevant_chunks:
            return 0.0
            
        # Take only first k results
        top_k_retrieved = set(retrieved_chunks[:k])
        relevant_set = set(relevant_chunks)
        
        # Number of relevant documents in top-k results
        relevant_in_top_k = len(top_k_retrieved.intersection(relevant_set))
        
        # Recall@k = relevant in top-k / total relevant
        recall = relevant_in_top_k / len(relevant_set)
        
        return recall
        
    def evaluate_system(self, assessment_file: str, output_file: str = None) -> Dict[str, Any]:
        """
        Evaluate RAG system using Recall@k metric.
        
        Args:
            assessment_file: Path to assessment.json file
            output_file: File to save results
            
        Returns:
            Dictionary with evaluation results
        """
        if output_file is None:
            output_file = f"recall_{self.k}_evaluation_results.json"
            
        # Load assessment data
        assessment_data = self.load_assessment_data(assessment_file)
        
        results = []
        recall_scores = []
        
        logger.info(f"Starting evaluation of {len(assessment_data)} questions with parameter k={self.k}")
        
        for question_id, data in assessment_data.items():
            question = data["question"]
            relevant_chunks = data["relevant_chunks"]
            
            logger.info(f"Processing question {question_id}: {question}")
            
            try:
                # Query API with number of results = k
                api_response = self.query_api(question, max_results=self.k)
                
                if "error" in api_response:
                    logger.error(f"API error for question {question_id}: {api_response['error']}")
                    result = {
                        "question_id": question_id,
                        "question": question,
                        "relevant_chunks": relevant_chunks,
                        "retrieved_chunks": [],
                        f"recall_at_{self.k}": 0.0,
                        "error": api_response["error"]
                    }
                else:
                    # Extract chunk_ids from response
                    retrieved_chunks = api_response.get("chunk_ids", [])
                    
                    # Calculate Recall@k
                    recall_at_k = self.calculate_recall_at_k(relevant_chunks, retrieved_chunks)
                    recall_scores.append(recall_at_k)
                    
                    result = {
                        "question_id": question_id,
                        "question": question,
                        "relevant_chunks": relevant_chunks,
                        "retrieved_chunks": retrieved_chunks,
                        f"recall_at_{self.k}": recall_at_k,
                        "relevant_count": len(relevant_chunks),
                        "retrieved_count": len(retrieved_chunks),
                        f"intersection_count_top_{self.k}": len(set(relevant_chunks).intersection(set(retrieved_chunks[:self.k])))
                    }
                    
                    logger.info(f"Question {question_id}: Recall@{self.k} = {recall_at_k:.3f}")
                
                results.append(result)
                
                # Add delay between requests
                time.sleep(1.0)
                
            except Exception as e:
                logger.error(f"Error processing question {question_id}: {e}")
                result = {
                    "question_id": question_id,
                    "question": question,
                    "relevant_chunks": relevant_chunks,
                    "retrieved_chunks": [],
                    f"recall_at_{self.k}": 0.0,
                    "error": str(e)
                }
                results.append(result)
        
        # Calculate overall statistics
        if recall_scores:
            avg_recall = sum(recall_scores) / len(recall_scores)
            max_recall = max(recall_scores)
            min_recall = min(recall_scores)
            
            # Count questions with different recall levels
            perfect_recall_count = sum(1 for score in recall_scores if score == 1.0)
            zero_recall_count = sum(1 for score in recall_scores if score == 0.0)
        else:
            avg_recall = max_recall = min_recall = 0.0
            perfect_recall_count = zero_recall_count = 0
        
        summary = {
            "k_parameter": self.k,
            "total_questions": len(assessment_data),
            "successful_evaluations": len(recall_scores),
            f"average_recall_at_{self.k}": avg_recall,
            f"max_recall_at_{self.k}": max_recall,
            f"min_recall_at_{self.k}": min_recall,
            "perfect_recall_count": perfect_recall_count,
            "zero_recall_count": zero_recall_count,
            "perfect_recall_percentage": (perfect_recall_count / len(recall_scores) * 100) if recall_scores else 0,
            "zero_recall_percentage": (zero_recall_count / len(recall_scores) * 100) if recall_scores else 0
        }
        
        # Prepare final results
        final_results = {
            "summary": summary,
            "detailed_results": results
        }
        
        # Save results
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(final_results, f, ensure_ascii=False, indent=2)
            
        logger.info(f"Results saved to {output_file}")
        logger.info(f"Average Recall@{self.k}: {avg_recall:.3f}")
        logger.info(f"Perfect recall ({perfect_recall_count}/{len(recall_scores)}): {perfect_recall_count / len(recall_scores) * 100:.1f}%")
        
        return final_results
        
    def print_summary(self, results: Dict[str, Any]) -> None:
        """
        Print brief summary of results.
        
        Args:
            results: Evaluation results
        """
        summary = results["summary"]
        k = summary["k_parameter"]
        
        print("\n" + "="*60)
        print(f"RECALL@{k} EVALUATION RESULTS")
        print("="*60)
        print(f"Parameter k: {k}")
        print(f"Total questions: {summary['total_questions']}")
        print(f"Successfully processed: {summary['successful_evaluations']}")
        print(f"Average Recall@{k}: {summary[f'average_recall_at_{k}']:.3f}")
        print(f"Maximum Recall@{k}: {summary[f'max_recall_at_{k}']:.3f}")
        print(f"Minimum Recall@{k}: {summary[f'min_recall_at_{k}']:.3f}")
        print(f"Questions with perfect recall (1.0): {summary['perfect_recall_count']} ({summary['perfect_recall_percentage']:.1f}%)")
        print(f"Questions with zero recall (0.0): {summary['zero_recall_count']} ({summary['zero_recall_percentage']:.1f}%)")
        print("="*60)

def parse_arguments():
    """
    Parse command line arguments.
    
    Returns:
        Object with command line arguments
    """
    parser = argparse.ArgumentParser(
        description="Evaluate RAG system using Recall@k metric",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage examples:
  python recall_evaluator.py --k 3                                    # Recall@3 (default)
  python recall_evaluator.py --k 5 --api http://localhost:8000        # Recall@5 on localhost
  python recall_evaluator.py --k 1 --assessment my_data.json          # Recall@1 with custom data
  python recall_evaluator.py --k 10 --output results_10.json          # Recall@10 with custom output
        """
    )
    
    parser.add_argument(
        "--k", 
        type=int, 
        default=3,
        help="Parameter k for Recall@k metric (default: 3)"
    )
    
    parser.add_argument(
        "--api",
        type=str,
        default="http://0.0.0.0:8000",
        help="Base API URL (default: http://0.0.0.0:8000)"
    )
    
    parser.add_argument(
        "--assessment",
        type=str,
        default="assessment.json",
        help="Path to assessment.json file (default: assessment.json)"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        help="Path to results output file (default: recall_{k}_evaluation_results.json)"
    )
    
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay between requests in seconds (default: 1.0)"
    )
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    return parser.parse_args()

def main():
    # Parse command line arguments
    args = parse_arguments()
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Parameter validation
    if args.k <= 0:
        logger.error(f"Parameter k must be positive, got: {args.k}")
        return
    
    if not Path(args.assessment).exists():
        logger.error(f"Assessment file not found: {args.assessment}")
        return
    
    logger.info(f"Starting evaluation with parameters:")
    logger.info(f"  k = {args.k}")
    logger.info(f"  API URL = {args.api}")
    logger.info(f"  Assessment file = {args.assessment}")
    logger.info(f"  Delay between requests = {args.delay}s")
    
    # Create evaluator instance
    evaluator = RecallEvaluator(args.api, k=args.k)
    
    try:
        # Run evaluation
        results = evaluator.evaluate_system(args.assessment, args.output)
        
        # Print summary
        evaluator.print_summary(results)
        
        # Additional information for analysis
        if args.verbose:
            print(f"\nDetailed information:")
            print(f"Results file: {args.output or f'recall_{args.k}_evaluation_results.json'}")
            print(f"Log file: recall_evaluation.log")
        
    except Exception as e:
        logger.error(f"Critical error: {e}")
        raise

if __name__ == "__main__":
    main()