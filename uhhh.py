import subprocess
import json
import os
import numpy as np
from skopt import gp_minimize
from skopt.space import Real, Integer
from skopt.utils import use_named_args
import tempfile
import shutil
import re

# Configuration
TRADER_FILE = "trader.py"
ROUNDS_TO_TEST = "1"
PRODUCTS = ["RAINFOREST_RESIN", "KELP", "SQUID_INK"]
MAX_EVALUATIONS = 50
PARALLEL_WORKERS = 4

PARAM_SPACES = {
    "RAINFOREST_RESIN": [
        Real(0.5, 2.5, name='take_width'),
        Real(0.5, 3.0, name='clear_width'),
        Integer(0, 2, name='disregard_edge'),
        Integer(1, 3, name='join_edge'),
        Integer(2, 4, name='default_edge')
    ],
    "KELP": [
        Real(0.5, 2.5, name='take_width'),
        Real(0.0, 1.5, name='clear_width'),
        Integer(10, 25, name='adverse_volume'),
        Real(-0.3, -0.1, name='reversion_beta'),
        Integer(0, 2, name='disregard_edge'),
        Integer(0, 2, name='join_edge'),
        Integer(1, 3, name='default_edge')
    ],
    "SQUID_INK": [
        Real(0.5, 2.5, name='take_width'),
        Real(0.0, 1.5, name='clear_width'),
        Integer(10, 25, name='adverse_volume'),
        Real(-0.3, -0.1, name='reversion_beta'),
        Integer(0, 2, name='disregard_edge'),
        Integer(0, 2, name='join_edge'),
        Integer(1, 3, name='default_edge')
    ]
}

class ParameterOptimizer:
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        self.results = {}
        self.original_code = self._load_trader_code()
        self.original_params = self._extract_params()
        
    def __del__(self):
        shutil.rmtree(self.temp_dir)

    def _load_trader_code(self):
        """Load the original trader code"""
        with open(TRADER_FILE, 'r') as f:
            return f.read()

    def _extract_params(self):
        """Extract PRODUCT_PARAMS using regex that handles class structure"""
        pattern = r"class Trader:.*?PRODUCT_PARAMS = (\{.*?\})"
        match = re.search(pattern, self.original_code, re.DOTALL)
        
        if not match:
            raise ValueError("PRODUCT_PARAMS dictionary not found in Trader class")
            
        try:
            # Create a minimal namespace with Product class mock
            namespace = {
                'Product': type('Product', (), {
                    'RAINFOREST_RESIN': "RAINFOREST_RESIN",
                    'KELP': "KELP",
                    'SQUID_INK': "SQUID_INK"
                })
            }
            exec(f"params = {match.group(1)}", namespace)
            return namespace['params']
        except Exception as e:
            raise ValueError(f"Could not parse PRODUCT_PARAMS: {e}")

    def optimize_product(self, product):
        print(f"\n=== Optimizing {product} ===")
        
        space = PARAM_SPACES[product]
        param_names = [dim.name for dim in space]
        
        @use_named_args(space)
        def objective(**params):
            return -self._run_backtest_with_params(product, params)
        
        result = gp_minimize(
            objective,
            space,
            n_calls=MAX_EVALUATIONS,
            random_state=42,
            n_jobs=PARALLEL_WORKERS
        )
        
        best_params = {
            k: float(v) if isinstance(v, np.floating) else int(v) if isinstance(v, np.integer) else v
            for k, v in dict(zip(param_names, result.x)).items()
        }
        
        self.results[product] = {
            'best_params': best_params,
            'best_pnl': float(-result.fun),
            'history': [float(-val) for val in result.func_vals]
        }
        
    def _run_backtest_with_params(self, product, params):
        """Run backtest with modified parameters"""
        try:
            modified_code = self._generate_modified_code(product, params)
            temp_file = os.path.join(self.temp_dir, f"temp_{product}.py")
            
            with open(temp_file, 'w') as f:
                f.write(modified_code)
            
            cmd = [
                "prosperity3bt",
                temp_file,
                ROUNDS_TO_TEST,
                "--merge-pnl",
                "--no-out"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            return self._parse_pnl(result.stdout)
        
        except Exception as e:
            print(f"Error in backtest: {str(e)[:100]}...")
            return -1e9

    def _generate_modified_code(self, product, params):
        """Generate code with updated parameters while preserving class structure"""
        new_params = json.loads(json.dumps(self.original_params))
        new_params[product].update(params)
        
        # Convert to properly formatted string
        params_str = json.dumps(new_params, indent=4)
        params_str = params_str.replace('"', '')  # Remove quotes for class references
        
        # Replace using regex that maintains class structure
        pattern = r"(class Trader:.*?PRODUCT_PARAMS = )\{.*?\}(.*?def __init__)"
        replacement = f"\\1{params_str}\\2"
        modified_code = re.sub(pattern, replacement, self.original_code, flags=re.DOTALL)
        
        return modified_code

    def _parse_pnl(self, output):
        for line in output.split('\n'):
            if line.startswith("Final PnL:"):
                return float(line.split(":")[1].strip())
        return -1e9

    def save_results(self, filename="optimized_params.json"):
        simplified = {
            product: {
                **data['best_params'],
                'pnl': data['best_pnl']
            }
            for product, data in self.results.items()
        }
        
        with open(filename, 'w') as f:
            json.dump(simplified, f, indent=4, default=lambda o: float(o) if isinstance(o, (np.floating, np.integer)) else str(o))

def main():
    optimizer = ParameterOptimizer()
    
    try:
        for product in PRODUCTS:
            optimizer.optimize_product(product)
        
        optimizer.save_results()
        print("\nOptimization complete!")
        
        print("\nBest Parameters:")
        for product, data in optimizer.results.items():
            print(f"\n{product}:")
            print(f"  PnL: {data['best_pnl']:.2f}")
            for param, value in data['best_params'].items():
                print(f"  {param}: {value}")
                
    except KeyboardInterrupt:
        print("\nOptimization interrupted! Saving partial results...")
        optimizer.save_results("partial_optimized_params.json")

if __name__ == "__main__":
    main()