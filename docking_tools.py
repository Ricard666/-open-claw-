#!/usr/bin/env python3
"""
docking_tools.py
   - 定义 Agent 可调用的对接工具
   - 每个工具通过 @tool 装饰器注册到 OpenClaw 框架
"""

import time
import subprocess
from openclaw import tool, Context
from docking_utils import DockingUtils


class DockingTools:
    def __init__(self):
        self.utils = DockingUtils()

    @tool(name="batch_docking", description="对给定的受体和配体列表进行批量对接")
    def batch_docking(self, ctx: Context, receptor_pdbqt: str, ligands_list: list) -> dict:
        """批量调用 AutoDock Vina 对接"""
        results = []
        for lig_path in ligands_list:
            start_time = time.time()
            try:
                # 假设 config.txt 给定对接盒参数
                cmd = [
                    "vina", "--config", "config.txt",
                    "--receptor", receptor_pdbqt,
                    "--ligand", lig_path,
                    "--out", f"out_{os.path.basename(lig_path)}.pdbqt"
                ]
                proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
                docking_time = time.time() - start_time
                parsed = self.utils.parse_vina_output(proc.stdout)
                parsed.update({
                    "receptor_path": receptor_pdbqt,
                    "ligand_path": lig_path,
                    "docking_time": docking_time,
                    "status": "success",
                    "log": proc.stdout,
                    "output_pdbqt": f"out_{os.path.basename(lig_path)}.pdbqt"
                })
                self.utils.save_docking_result(parsed)
                results.append(parsed)
            except subprocess.CalledProcessError as e:
                self.utils.save_docking_result({
                    "receptor_path": receptor_pdbqt,
                    "ligand_path": lig_path,
                    "status": "failed",
                    "log": e.stderr
                })
                results.append({"error": str(e), "ligand": lig_path})
        return {"results": results, "summary": f"成功对接 {len([r for r in results if 'error' not in r])}/{len(ligands_list)} 个配体"}

    @tool(name="get_top_affinity", description="返回对接评分前 N 的配体")
    def get_top_affinity(self, ctx: Context, top_n: int = 10) -> List[Tuple]:
        return self.utils.get_best_ligands(top_n)

    @tool(name="preprocess_structure", description="将受体/配体原始文件预处理为 PDBQT 格式")
    def preprocess_structure(self, ctx: Context, input_path: str, output_path: str, mol_type: str = "ligand") -> str:
        if mol_type == "ligand":
            return self.utils.preprocess_ligand(input_path, output_path)
        else:
            return self.utils.preprocess_receptor(input_path, output_path)
