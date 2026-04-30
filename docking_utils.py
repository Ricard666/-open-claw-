#!/usr/bin/env python3
"""
docking_utils.py
   - 文件与配体预处理
   - 对接结果解析与评分提取
   - 简化对接、评分表的处理
"""

import os
import subprocess
import sqlite3
import shutil
from typing import Dict, List, Optional, Tuple


class DockingUtils:
    def __init__(self, db_path: str = "docking_results.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """初始化对接结果 SQLite 存储"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS docking_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    receptor_path TEXT,
                    ligand_path TEXT,
                    binding_affinity REAL,
                    rmsd_ub REAL,
                    rmsd_lb REAL,
                    output_pdbqt TEXT,
                    docking_time REAL,
                    status TEXT,
                    log TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ligands_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ligand_name TEXT UNIQUE,
                    file_path TEXT,
                    smiles TEXT,
                    mol_weight REAL,
                    logp REAL
                )
            """)

    def preprocess_ligand(self, ligand_sdf: str, output_pdbqt: str):
        """配体预处理：SDF 转 PDBQT
        实际可调用 openbabel/obabel 或 MGLTools 脚本
        """
        cmd = ["obabel", ligand_sdf, "-O", output_pdbqt, "-h"]
        subprocess.run(cmd, check=True)
        return output_pdbqt

    def preprocess_receptor(self, receptor_pdb: str, output_pdbqt: str):
        """受体预处理：PDB -> PDBQT（加氢、合并电荷）"""
        cmd = ["prepare_receptor4.py", "-r", receptor_pdb, "-o", output_pdbqt]
        subprocess.run(cmd, check=True)
        return output_pdbqt

    def parse_vina_output(self, log_text: str) -> Dict:
        """解析 AutoDock Vina 标准输出，提取对接分数"""
        affinity = None
        rmsd_ub = None
        rmsd_lb = None
        for line in log_text.splitlines():
            if "Affinity" in line:
                parts = line.split()
                try:
                    affinity = float(parts[-1])
                except:
                    pass
            if "rmsd l.b." in line.lower():
                parts = line.split()
                try:
                    rmsd_lb = float(parts[-1])
                except:
                    pass
            if "rmsd u.b." in line.lower():
                parts = line.split()
                try:
                    rmsd_ub = float(parts[-1])
                except:
                    pass
        return {
            "binding_affinity": affinity,
            "rmsd_lb": rmsd_lb,
            "rmsd_ub": rmsd_ub,
        }

    def save_docking_result(self, data: Dict):
        """将对接结果存入数据库"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO docking_results (
                    receptor_path, ligand_path, binding_affinity, rmsd_ub, rmsd_lb,
                    output_pdbqt, docking_time, status, log
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get("receptor_path"),
                data.get("ligand_path"),
                data.get("binding_affinity"),
                data.get("rmsd_ub"),
                data.get("rmsd_lb"),
                data.get("output_pdbqt"),
                data.get("docking_time"),
                data.get("status"),
                data.get("log")
            ))

    def get_best_ligands(self, top_n: int = 10) -> List[Tuple]:
        """查询对接分数最好的 N 个配体"""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("""
                SELECT ligand_path, binding_affinity FROM docking_results
                WHERE status = 'success'
                ORDER BY binding_affinity ASC
                LIMIT ?
            """, (top_n,))
            return cur.fetchall()
