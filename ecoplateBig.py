import argparse
import glob
import os
import re
import pandas as pd

# Microplate Software Grid Layout (Row Letters A-H, Column Numbers 1-12)
GRID_LAYOUT = {
    'Water': ['A1', 'A5', 'A9'],
    'β-Methyl-D-Glucoside': ['A2', 'A6', 'A10'],
    'D-Galactonic Acid γ-Lactone': ['A3', 'A7', 'A11'],
    'L-Arginine': ['A4', 'A8', 'A12'],
    'Pyruvic Acid Methyl Ester': ['B1', 'B5', 'B9'],
    'D-Xylose': ['B2', 'B6', 'B10'],
    'D-Galacturonic Acid': ['B3', 'B7', 'B11'],
    'L-Asparagine': ['B4', 'B8', 'B12'],
    'Tween 40': ['C1', 'C5', 'C9'],
    'i-Erythritol': ['C2', 'C6', 'C10'],
    '2-Hydroxy Benzoic Acid': ['C3', 'C7', 'C11'],
    'L-Phenylalanine': ['C4', 'C8', 'C12'],
    'Tween 80': ['D1', 'D5', 'D9'],
    'D-Mannitol': ['D2', 'D6', 'D10'],
    '4-Hydroxy Benzoic Acid': ['D3', 'D7', 'D11'],
    'L-Serine': ['D4', 'D8', 'D12'],
    'α-Cyclodextrin': ['E1', 'E5', 'E9'],
    'N-Acetyl-D-Glucosamine': ['E2', 'E6', 'E10'],
    'γ-Amino Butyric Acid': ['E3', 'E7', 'E11'],
    'L-Threonine': ['E4', 'E8', 'E12'],
    'Glycogen': ['F1', 'F5', 'F9'],
    'D-Glucosaminic Acid': ['F2', 'F6', 'F10'],
    'Itaconic Acid': ['F3', 'F7', 'F11'],
    'β-Hydroxy-Glycyl-L-Glutamic Acid': ['F4', 'F8', 'F12'],
    'D-Cellobiose': ['G1', 'G5', 'G9'],
    'Glucose-1-Phosphate': ['G2', 'G6', 'G10'],
    'α-Keto Butyric Acid': ['G3', 'G7', 'G11'],
    'Phenylethylamine': ['G4', 'G8', 'G12'],
    'α-D-Lactose': ['H1', 'H5', 'H9'],
    'D,L-α-Glycerol Phosphate': ['H2', 'H6', 'H10'],
    'D-Malic Acid': ['H3', 'H7', 'H11'],
    'Putrescine': ['H4', 'H8', 'H12']
}

def extract_file_info(filepath):
    """Extracts sampl-id and day from filename or parent subfolder path."""
    filename = os.path.basename(filepath)
    clean_name = os.path.splitext(filename)[0]
    
    # 1. Check filename for 'day' (e.g. 't6_m_day5.xlsx')
    match = re.search(r'^(.*?)[_-]?day[_-]?(\d+)', clean_name, re.IGNORECASE)
    if match:
        sample_id = match.group(1).rstrip('_ -')
        day = int(match.group(2))
        return sample_id, day

    # 2. Check parent folder name for 'day' (e.g. '/Day 5/t6_m.xlsx')
    parent_folder = os.path.basename(os.path.dirname(filepath))
    folder_match = re.search(r'day[_-]?(\d+)', parent_folder, re.IGNORECASE)
    if folder_match:
        day = int(folder_match.group(1))
        return clean_name, day

    return clean_name, None

def extract_plate_df(filepath):
    """Locates the 8x12 numerical grid inside the raw Excel sheet."""
    df_raw = pd.read_excel(filepath, header=None)
    
    for idx in range(len(df_raw)):
        row_str = [str(x).strip().upper() for x in df_raw.iloc[idx].values]
        if 'A' in row_str and idx + 1 < len(df_raw) and 'B' in [str(x).strip().upper() for x in df_raw.iloc[idx+1].values]:
            a_idx = idx
            c_start = row_str.index('A') + 1
            
            matrix = df_raw.iloc[a_idx:a_idx+8, c_start:c_start+12].values.astype(float)
            rows = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
            cols = list(range(1, 13))
            return pd.DataFrame(matrix, index=rows, columns=cols)
            
    raise ValueError(f"Could not locate 8x12 plate matrix in file: {filepath}")

def process_file(filepath):
    sample_id, day = extract_file_info(filepath)
    plate_df = extract_plate_df(filepath)
    
    # Average the 3 replicate wells per carbon source
    cs_means = {}
    for cs, wells in GRID_LAYOUT.items():
        vals = [plate_df.loc[w[0], int(w[1:])] for w in wells]
        cs_means[cs] = sum(vals) / len(vals)
        
    water_val = cs_means['Water']

    # Build complete row records INCLUDING Water
    records = []
    for cs, mean_val in cs_means.items():
        adj_awcd = mean_val - water_val
        records.append({
            'sampl-id': sample_id,
            'day': day,
            'carbon source': cs,
            'AWCD': mean_val,
            'adjusted awcd': adj_awcd
        })
        
    return pd.DataFrame(records)

def batch_consolidate(input_folder, output_file="Master_Consolidated_Data.xlsx"):
    all_files = []
    for root, dirs, files in os.walk(input_folder):
        for file in files:
            if (file.endswith('.xlsx') or file.endswith('.xls')) and not file.startswith('~$'):
                all_files.append(os.path.join(root, file))
                
    all_files = [f for f in all_files if output_file not in f]
    
    if not all_files:
        print("No Excel files found in the specified folder or subfolders.")
        return
        
    print(f"Found {len(all_files)} Excel files across subfolders...")
    all_dfs = []
    
    for f in all_files:
        try:
            df_processed = process_file(f)
            all_dfs.append(df_processed)
            print(f"  [✓] Processed: {os.path.relpath(f, input_folder)}")
        except Exception as e:
            print(f"  [X] Failed {os.path.relpath(f, input_folder)}: {e}")
            
    if not all_dfs:
        print("No files were successfully processed.")
        return
        
    master_df = pd.concat(all_dfs, ignore_index=True)
    out_path = os.path.join(input_folder, output_file)
    
    # Select and order final output columns
    final_cols = ['sampl-id', 'day', 'carbon source', 'AWCD', 'adjusted awcd']
    master_df[final_cols].to_excel(out_path, index=False, sheet_name="Consolidated Data")
    print(f"\n[Success] Consolidated {len(all_dfs)} files into: {out_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Consolidate EcoPlate Excel data across subfolders from command line."
    )
    parser.add_argument(
        "folder_path",
        type=str,
        help="Target folder containing Excel files or Day subfolders."
    )
    
    args = parser.parse_args()
    target_folder = os.path.abspath(args.folder_path)
    
    if not os.path.isdir(target_folder):
        print(f"[Error] Provided folder path does not exist or is not a directory:\n{target_folder}")
    else:
        print(f"Scanning directory: {target_folder}\n")
        batch_consolidate(input_folder=target_folder)