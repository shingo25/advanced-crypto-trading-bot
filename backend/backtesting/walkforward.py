import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Callable
from datetime import datetime, timedelta
from concurrent.futures import ProcessPoolExecutor, as_completed
import logging
from pathlib import Path
import json

from .engine import BacktestEngine, BacktestResult

logger = logging.getLogger(__name__)


class WalkForwardAnalysis:
    """ウォークフォワード分析クラス"""
    
    def __init__(self, 
                 lookback_days: int = 90,
                 forward_days: int = 30,
                 rebalance_frequency: int = 30,
                 min_trades_threshold: int = 10):
        
        self.lookback_days = lookback_days
        self.forward_days = forward_days
        self.rebalance_frequency = rebalance_frequency
        self.min_trades_threshold = min_trades_threshold
        
        self.optimization_results: List[Dict[str, Any]] = []
        self.forward_test_results: List[BacktestResult] = []
        
        logger.info(f"WalkForwardAnalysis initialized: lookback={lookback_days}d, forward={forward_days}d")
    
    def run_analysis(self, 
                    data: pd.DataFrame,
                    strategy_func: Callable,
                    parameter_ranges: Dict[str, Any],
                    optimization_metric: str = 'sharpe_ratio',
                    initial_capital: float = 10000.0,
                    max_workers: int = 4) -> Dict[str, Any]:
        """ウォークフォワード分析を実行"""
        
        logger.info("Starting walk-forward analysis...")
        
        # 日付でソート
        data = data.sort_values('timestamp')
        
        # 分析期間を決定
        start_date = data['timestamp'].min()
        end_date = data['timestamp'].max()
        
        # ウォークフォワード期間を生成
        periods = self._generate_periods(start_date, end_date)
        
        logger.info(f"Generated {len(periods)} walk-forward periods")
        
        # 各期間で最適化とテストを実行
        results = []
        
        for i, (opt_start, opt_end, test_start, test_end) in enumerate(periods):
            logger.info(f"Processing period {i+1}/{len(periods)}: {opt_start.date()} to {test_end.date()}")
            
            # 最適化期間のデータ
            opt_data = data[(data['timestamp'] >= opt_start) & (data['timestamp'] < opt_end)]
            
            # テスト期間のデータ
            test_data = data[(data['timestamp'] >= test_start) & (data['timestamp'] < test_end)]
            
            if len(opt_data) < 100 or len(test_data) < 20:
                logger.warning(f"Insufficient data for period {i+1}, skipping...")
                continue
            
            # パラメータ最適化
            best_params = self._optimize_parameters(
                opt_data,
                strategy_func,
                parameter_ranges,
                optimization_metric,
                initial_capital,
                max_workers
            )
            
            # フォワードテスト
            forward_result = self._run_forward_test(
                test_data,
                strategy_func,
                best_params,
                initial_capital
            )
            
            results.append({
                'period': i + 1,
                'optimization_start': opt_start,
                'optimization_end': opt_end,
                'test_start': test_start,
                'test_end': test_end,
                'best_params': best_params,
                'forward_result': forward_result
            })
        
        # 結果の統合
        analysis_result = self._combine_results(results)
        
        logger.info("Walk-forward analysis completed")
        return analysis_result
    
    def _generate_periods(self, 
                         start_date: datetime,
                         end_date: datetime) -> List[Tuple[datetime, datetime, datetime, datetime]]:
        """ウォークフォワード期間を生成"""
        
        periods = []
        current_date = start_date
        
        while current_date < end_date:
            # 最適化期間
            opt_start = current_date
            opt_end = current_date + timedelta(days=self.lookback_days)
            
            # テスト期間
            test_start = opt_end
            test_end = opt_end + timedelta(days=self.forward_days)
            
            # 終了日を超えない
            if test_end > end_date:
                test_end = end_date
            
            if test_start < end_date:
                periods.append((opt_start, opt_end, test_start, test_end))
            
            # 次の期間へ
            current_date += timedelta(days=self.rebalance_frequency)
        
        return periods
    
    def _optimize_parameters(self, 
                            data: pd.DataFrame,
                            strategy_func: Callable,
                            parameter_ranges: Dict[str, Any],
                            optimization_metric: str,
                            initial_capital: float,
                            max_workers: int) -> Dict[str, Any]:
        """パラメータを最適化"""
        
        # パラメータ組み合わせを生成
        param_combinations = self._generate_parameter_combinations(parameter_ranges)
        
        logger.info(f"Testing {len(param_combinations)} parameter combinations")
        
        # 並列実行
        results = []
        
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            
            for params in param_combinations:
                future = executor.submit(
                    self._test_parameter_combination,
                    data,
                    strategy_func,
                    params,
                    initial_capital
                )
                futures.append((future, params))
            
            # 結果を収集
            for future, params in futures:
                try:
                    result = future.result()
                    if result and result.total_trades >= self.min_trades_threshold:
                        results.append({
                            'params': params,
                            'result': result,
                            'metric_value': self._get_metric_value(result, optimization_metric)
                        })
                except Exception as e:
                    logger.error(f"Error testing parameters {params}: {e}")
        
        # 最適なパラメータを選択
        if not results:
            logger.warning("No valid parameter combinations found")
            return {}
        
        best_result = max(results, key=lambda x: x['metric_value'])
        
        logger.info(f"Best parameters found: {best_result['params']}")
        logger.info(f"Best {optimization_metric}: {best_result['metric_value']:.4f}")
        
        return best_result['params']
    
    def _generate_parameter_combinations(self, parameter_ranges: Dict[str, Any]) -> List[Dict[str, Any]]:
        """パラメータ組み合わせを生成"""
        
        import itertools
        
        # パラメータ名と値の範囲を取得
        param_names = []
        param_values = []
        
        for name, value_range in parameter_ranges.items():
            param_names.append(name)
            
            if isinstance(value_range, dict) and 'min' in value_range and 'max' in value_range:
                # 数値範囲の場合
                min_val = value_range['min']
                max_val = value_range['max']
                step = value_range.get('step', 1)
                
                if isinstance(min_val, float) or isinstance(max_val, float):
                    # 浮動小数点数の場合
                    values = np.arange(min_val, max_val + step, step)
                else:
                    # 整数の場合
                    values = range(min_val, max_val + step, step)
                
                param_values.append(list(values))
            
            elif isinstance(value_range, list):
                # リストの場合
                param_values.append(value_range)
            else:
                # 単一値の場合
                param_values.append([value_range])
        
        # 全組み合わせを生成
        combinations = []
        for combination in itertools.product(*param_values):
            param_dict = dict(zip(param_names, combination))
            combinations.append(param_dict)
        
        return combinations
    
    def _test_parameter_combination(self, 
                                   data: pd.DataFrame,
                                   strategy_func: Callable,
                                   params: Dict[str, Any],
                                   initial_capital: float) -> Optional[BacktestResult]:
        """パラメータ組み合わせをテスト"""
        
        try:
            # バックテストエンジンを初期化
            engine = BacktestEngine(initial_capital=initial_capital)
            
            # 戦略を実行
            for _, row in data.iterrows():
                ohlcv = {
                    'open': row['open'],
                    'high': row['high'],
                    'low': row['low'],
                    'close': row['close'],
                    'volume': row['volume']
                }
                
                # 戦略シグナルを生成
                signals = strategy_func(row, params)
                
                # バーを処理
                engine.process_bar(
                    timestamp=row['timestamp'],
                    ohlcv=ohlcv,
                    signals=signals,
                    strategy_name=f"test_{hash(str(params))}"
                )
            
            # 結果を取得
            return engine.get_results(f"optimization_{hash(str(params))}")
            
        except Exception as e:
            logger.error(f"Error in parameter test: {e}")
            return None
    
    def _get_metric_value(self, result: BacktestResult, metric: str) -> float:
        """最適化メトリクスの値を取得"""
        
        if metric == 'sharpe_ratio':
            return result.sharpe_ratio
        elif metric == 'total_return':
            return result.total_return
        elif metric == 'profit_factor':
            return result.profit_factor
        elif metric == 'win_rate':
            return result.win_rate
        elif metric == 'sortino_ratio':
            return result.sortino_ratio
        elif metric == 'calmar_ratio':
            return result.calmar_ratio
        else:
            return result.sharpe_ratio  # デフォルト
    
    def _run_forward_test(self, 
                         data: pd.DataFrame,
                         strategy_func: Callable,
                         params: Dict[str, Any],
                         initial_capital: float) -> BacktestResult:
        """フォワードテストを実行"""
        
        engine = BacktestEngine(initial_capital=initial_capital)
        
        for _, row in data.iterrows():
            ohlcv = {
                'open': row['open'],
                'high': row['high'],
                'low': row['low'],
                'close': row['close'],
                'volume': row['volume']
            }
            
            signals = strategy_func(row, params)
            
            engine.process_bar(
                timestamp=row['timestamp'],
                ohlcv=ohlcv,
                signals=signals,
                strategy_name="forward_test"
            )
        
        return engine.get_results("forward_test")
    
    def _combine_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """結果を統合"""
        
        if not results:
            return {}
        
        # 各期間の結果を統合
        combined_trades = []
        combined_equity = []
        
        for result in results:
            forward_result = result['forward_result']
            combined_trades.extend(forward_result.trades)
            
            # 資産曲線を調整
            if combined_equity:
                last_equity = combined_equity[-1]['equity']
                initial_capital = forward_result.initial_capital
                adjustment_factor = last_equity / initial_capital
                
                adjusted_equity = forward_result.equity_curve.copy()
                adjusted_equity['equity'] *= adjustment_factor
                adjusted_equity['cash'] *= adjustment_factor
                
                combined_equity.extend(adjusted_equity.to_dict('records'))
            else:
                combined_equity.extend(forward_result.equity_curve.to_dict('records'))
        
        # 全体のパフォーマンス統計を計算
        if combined_equity:
            equity_df = pd.DataFrame(combined_equity)
            initial_capital = equity_df['equity'].iloc[0]
            final_capital = equity_df['equity'].iloc[-1]
            total_return = (final_capital - initial_capital) / initial_capital
            
            # 最大ドローダウンを計算
            peak = equity_df['equity'].cummax()
            drawdown = (peak - equity_df['equity']) / peak
            max_drawdown = drawdown.max()
            
            # シャープレシオを計算
            returns = equity_df['equity'].pct_change().dropna()
            sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252 * 24) if returns.std() > 0 else 0
        else:
            initial_capital = 10000
            final_capital = 10000
            total_return = 0
            max_drawdown = 0
            sharpe_ratio = 0
        
        return {
            'periods': len(results),
            'initial_capital': initial_capital,
            'final_capital': final_capital,
            'total_return': total_return,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'combined_trades': combined_trades,
            'combined_equity': combined_equity,
            'period_results': results,
            'parameter_stability': self._analyze_parameter_stability(results)
        }
    
    def _analyze_parameter_stability(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """パラメータの安定性を分析"""
        
        if not results:
            return {}
        
        # 各パラメータの値の変化を追跡
        param_history = {}
        
        for result in results:
            params = result['best_params']
            
            for param_name, param_value in params.items():
                if param_name not in param_history:
                    param_history[param_name] = []
                param_history[param_name].append(param_value)
        
        # 安定性指標を計算
        stability_metrics = {}
        
        for param_name, values in param_history.items():
            if len(values) > 1:
                # 標準偏差
                std_dev = np.std(values)
                mean_val = np.mean(values)
                
                # 変動係数
                cv = std_dev / mean_val if mean_val != 0 else 0
                
                # 値の変化回数
                changes = sum(1 for i in range(1, len(values)) if values[i] != values[i-1])
                change_frequency = changes / (len(values) - 1) if len(values) > 1 else 0
                
                stability_metrics[param_name] = {
                    'mean': mean_val,
                    'std_dev': std_dev,
                    'coefficient_of_variation': cv,
                    'change_frequency': change_frequency,
                    'values': values
                }
        
        return stability_metrics
    
    def save_results(self, results: Dict[str, Any], output_dir: str = "walkforward_results"):
        """結果を保存"""
        
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # 全体結果を保存
        summary_file = output_path / "walkforward_summary.json"
        summary = {
            'periods': results['periods'],
            'initial_capital': results['initial_capital'],
            'final_capital': results['final_capital'],
            'total_return': results['total_return'],
            'max_drawdown': results['max_drawdown'],
            'sharpe_ratio': results['sharpe_ratio'],
            'parameter_stability': results['parameter_stability']
        }
        
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        # 取引履歴を保存
        if results['combined_trades']:
            trades_df = pd.DataFrame([trade.to_dict() for trade in results['combined_trades']])
            trades_file = output_path / "walkforward_trades.csv"
            trades_df.to_csv(trades_file, index=False)
        
        # 資産曲線を保存
        if results['combined_equity']:
            equity_df = pd.DataFrame(results['combined_equity'])
            equity_file = output_path / "walkforward_equity.csv"
            equity_df.to_csv(equity_file, index=False)
        
        # 期間別結果を保存
        for i, period_result in enumerate(results['period_results']):
            period_file = output_path / f"period_{i+1}_result.json"
            
            period_data = {
                'period': period_result['period'],
                'optimization_start': period_result['optimization_start'].isoformat(),
                'optimization_end': period_result['optimization_end'].isoformat(),
                'test_start': period_result['test_start'].isoformat(),
                'test_end': period_result['test_end'].isoformat(),
                'best_params': period_result['best_params'],
                'forward_result': {
                    'total_return': period_result['forward_result'].total_return,
                    'sharpe_ratio': period_result['forward_result'].sharpe_ratio,
                    'max_drawdown': period_result['forward_result'].max_drawdown,
                    'total_trades': period_result['forward_result'].total_trades,
                    'win_rate': period_result['forward_result'].win_rate
                }
            }
            
            with open(period_file, 'w') as f:
                json.dump(period_data, f, indent=2)
        
        logger.info(f"Walk-forward results saved to {output_path}")


class MonteCarloAnalysis:
    """モンテカルロ分析クラス"""
    
    def __init__(self, num_simulations: int = 1000):
        self.num_simulations = num_simulations
        
    def run_analysis(self, 
                    trades: List[Dict[str, Any]],
                    initial_capital: float = 10000.0) -> Dict[str, Any]:
        """モンテカルロ分析を実行"""
        
        logger.info(f"Starting Monte Carlo analysis with {self.num_simulations} simulations")
        
        if not trades:
            logger.error("No trades provided for Monte Carlo analysis")
            return {}
        
        # 取引からリターンを抽出
        returns = [trade['realized_pnl'] / initial_capital for trade in trades if trade['realized_pnl'] != 0]
        
        if not returns:
            logger.error("No profitable/losing trades found")
            return {}
        
        # シミュレーションを実行
        simulation_results = []
        
        for i in range(self.num_simulations):
            # ランダムに取引順序を並び替え
            shuffled_returns = np.random.choice(returns, size=len(returns), replace=True)
            
            # 資産曲線を計算
            equity_curve = [initial_capital]
            current_capital = initial_capital
            
            for return_val in shuffled_returns:
                current_capital += return_val * current_capital
                equity_curve.append(current_capital)
            
            # 最終資本と最大ドローダウンを計算
            final_capital = equity_curve[-1]
            peak = np.maximum.accumulate(equity_curve)
            drawdown = (peak - equity_curve) / peak
            max_drawdown = np.max(drawdown)
            
            simulation_results.append({
                'final_capital': final_capital,
                'total_return': (final_capital - initial_capital) / initial_capital,
                'max_drawdown': max_drawdown,
                'equity_curve': equity_curve
            })
        
        # 統計を計算
        final_capitals = [r['final_capital'] for r in simulation_results]
        total_returns = [r['total_return'] for r in simulation_results]
        max_drawdowns = [r['max_drawdown'] for r in simulation_results]
        
        results = {
            'simulations': self.num_simulations,
            'final_capital': {
                'mean': np.mean(final_capitals),
                'std': np.std(final_capitals),
                'min': np.min(final_capitals),
                'max': np.max(final_capitals),
                'percentiles': {
                    '5th': np.percentile(final_capitals, 5),
                    '25th': np.percentile(final_capitals, 25),
                    '50th': np.percentile(final_capitals, 50),
                    '75th': np.percentile(final_capitals, 75),
                    '95th': np.percentile(final_capitals, 95)
                }
            },
            'total_return': {
                'mean': np.mean(total_returns),
                'std': np.std(total_returns),
                'min': np.min(total_returns),
                'max': np.max(total_returns),
                'percentiles': {
                    '5th': np.percentile(total_returns, 5),
                    '25th': np.percentile(total_returns, 25),
                    '50th': np.percentile(total_returns, 50),
                    '75th': np.percentile(total_returns, 75),
                    '95th': np.percentile(total_returns, 95)
                }
            },
            'max_drawdown': {
                'mean': np.mean(max_drawdowns),
                'std': np.std(max_drawdowns),
                'min': np.min(max_drawdowns),
                'max': np.max(max_drawdowns),
                'percentiles': {
                    '5th': np.percentile(max_drawdowns, 5),
                    '25th': np.percentile(max_drawdowns, 25),
                    '50th': np.percentile(max_drawdowns, 50),
                    '75th': np.percentile(max_drawdowns, 75),
                    '95th': np.percentile(max_drawdowns, 95)
                }
            },
            'probability_of_loss': sum(1 for r in total_returns if r < 0) / len(total_returns),
            'simulation_results': simulation_results
        }
        
        logger.info("Monte Carlo analysis completed")
        return results
    
    def save_results(self, results: Dict[str, Any], output_dir: str = "montecarlo_results"):
        """結果を保存"""
        
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # 統計サマリーを保存
        summary_file = output_path / "montecarlo_summary.json"
        summary = {
            'simulations': results['simulations'],
            'final_capital': results['final_capital'],
            'total_return': results['total_return'],
            'max_drawdown': results['max_drawdown'],
            'probability_of_loss': results['probability_of_loss']
        }
        
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        # 全シミュレーション結果を保存
        simulation_data = []
        for i, sim_result in enumerate(results['simulation_results']):
            simulation_data.append({
                'simulation': i + 1,
                'final_capital': sim_result['final_capital'],
                'total_return': sim_result['total_return'],
                'max_drawdown': sim_result['max_drawdown']
            })
        
        sim_df = pd.DataFrame(simulation_data)
        sim_file = output_path / "montecarlo_simulations.csv"
        sim_df.to_csv(sim_file, index=False)
        
        logger.info(f"Monte Carlo results saved to {output_path}")