"""GPU 预测子进程

独立进程加载 XGBoost 模型并运行 GPU 预测，通过 multiprocessing.Queue
与 Flask 主进程通信，隔离 CUDA 上下文避免稳定性问题。
"""

import os
import json
import multiprocessing
import numpy as np
from typing import Optional


class GPUWorker:
    """GPU 预测工作进程"""

    def __init__(self, model_dir: str):
        self.model_path = os.path.join(model_dir, 'xgboost_model.json')
        self.meta_path = os.path.join(model_dir, 'xgboost_model_meta.json')
        self._model = None
        self._feature_cols = None
        self._input_queue: multiprocessing.Queue = multiprocessing.Queue()
        self._output_queue: multiprocessing.Queue = multiprocessing.Queue()
        self._process: Optional[multiprocessing.Process] = None
        self._request_id = 0

    def start(self):
        """启动 GPU 工作进程"""
        if self._process is not None:
            return
        self._process = multiprocessing.Process(
            target=_gpu_worker_loop,
            args=(self._input_queue, self._output_queue, self.model_path, self.meta_path),
            daemon=True,
        )
        self._process.start()

    def predict(self, X: np.ndarray) -> np.ndarray:
        """发送预测请求并等待结果

        Args:
            X: 输入特征矩阵 (n_samples, n_features)，dtype=float32

        Returns:
            预测结果数组 (n_samples,)
        """
        if self._process is None or not self._process.is_alive():
            self.start()

        self._request_id += 1
        rid = self._request_id
        X_bytes = X.astype(np.float32).tobytes()
        shape = X.shape
        self._input_queue.put((rid, X_bytes, shape))
        result_rid, result_bytes = self._output_queue.get()
        assert result_rid == rid, f"Request ID mismatch: {result_rid} != {rid}"
        return np.frombuffer(result_bytes, dtype=np.float32)

    def shutdown(self):
        """关闭工作进程"""
        if self._process is not None:
            self._process.terminate()
            self._process.join(timeout=5)
            self._process = None

    @property
    def feature_cols(self) -> list:
        if self._feature_cols is None:
            if os.path.exists(self.meta_path):
                with open(self.meta_path, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                self._feature_cols = meta.get('feature_cols', [])
            if not self._feature_cols:
                self._feature_cols = [
                    'ret_1d', 'ret_5d', 'volatility_5d', 'volatility_10d',
                    'vol_change_1d', 'turnover', 'turnover_change_1d',
                    'bias_3d', 'bias_5d', 'bias_20d',
                    'amplitude', 'close_shadow',
                    'ret_1d_rel', 'volatility_5d_rel', 'volatility_10d_rel',
                    'vol_change_1d_rel', 'turnover_rel', 'amplitude_rel', 'close_shadow_rel',
                ]
        return self._feature_cols


def _gpu_worker_loop(input_queue: multiprocessing.Queue,
                     output_queue: multiprocessing.Queue,
                     model_path: str,
                     meta_path: str):
    """GPU 工作进程的主循环"""
    import xgboost as xgb

    print("[GPU Worker] 启动中...")
    bst = xgb.XGBRanker()
    bst.load_model(model_path)
    booster = bst.get_booster()
    build_info = xgb.build_info()

    if build_info.get('USE_CUDA', False):
        booster.set_param({'device': 'cuda', 'nthread': 1})
        print("[GPU Worker] GPU 加速已启用 (CUDA)")
    else:
        booster.set_param({'device': 'cpu', 'nthread': 4})
        print("[GPU Worker] 编译时未启用 CUDA，使用 CPU")

    print("[GPU Worker] 就绪，等待预测请求...")

    while True:
        try:
            rid, X_bytes, shape = input_queue.get()
            X = np.frombuffer(X_bytes, dtype=np.float32).reshape(shape)

            batch_size = 1000
            if len(X) > batch_size:
                scores = np.empty(len(X), dtype=np.float32)
                for i in range(0, len(X), batch_size):
                    batch = X[i:i + batch_size]
                    scores[i:i + batch_size] = bst.predict(batch)
            else:
                scores = bst.predict(X).astype(np.float32)

            output_queue.put((rid, scores.tobytes()))
        except EOFError:
            break
        except Exception as e:
            print(f"[GPU Worker] 预测异常: {e}")
            output_queue.put((rid, np.array([0.0], dtype=np.float32).tobytes()))
