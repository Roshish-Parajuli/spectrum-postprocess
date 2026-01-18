import streamlit as st
import pandas as pd
import io
import re

st.set_page_config(page_title="CSV Address Processor", page_icon="📊", layout="wide")

def normalize_address(addr):
    """Normalize address for comparison"""
    if pd.isna(addr):
        return ""
    addr = str(addr).upper()
    addr = re.sub(r'\s+', ' ', addr)
    addr = re.sub(r'[.,#-]', '', addr)
    return addr.strip()

def get_input_row_from_location(location, input_df, address_col, suite_col, city_col, state_col, zip_col):
    """Find matching input row based on location string"""
    normalized_location = normalize_address(location)
    
    for idx, row in input_df.iterrows():
        full_address = str(row[address_col]) if pd.notna(row[address_col]) else ""
        
        if suite_col and pd.notna(row[suite_col]):
            full_address += " " + str(row[suite_col])
        
        full_address += " " + (str(row[city_col]) if pd.notna(row[city_col]) else "")
        full_address += " " + (str(row[state_col]) if pd.notna(row[state_col]) else "")
        
        if zip_col and pd.notna(row[zip_col]):
            full_address += " " + str(row[zip_col])
        
        if normalize_address(full_address) == normalized_location:
            return row
    
    return None

def process_csv_files(output_files, input_file):
    """Main processing logic"""
    results = {}
    
    # Step 1: Combine multiple CSV files
    all_dfs = []
    for file in output_files:
        df = pd.read_csv(file)
        all_dfs.append(df)
    
    merged_df = pd.concat(all_dfs, ignore_index=True)
    results['total_output'] = len(merged_df)
    
    # Step 2: Separate failed and valid records
    remarks_col = [col for col in merged_df.columns if 'remark' in col.lower()]
    
    if remarks_col:
        remarks_col = remarks_col[0]
        failed_df = merged_df[merged_df[remarks_col].str.contains('failed', case=False, na=False)].copy()
        valid_df = merged_df[~merged_df[remarks_col].str.contains('failed', case=False, na=False)].copy()
    else:
        failed_df = pd.DataFrame()
        valid_df = merged_df.copy()
    
    results['failed_removed'] = len(failed_df)
    results['valid_records'] = len(valid_df)
    
    # Step 3: Parse input file and compare
    input_df = pd.read_csv(input_file)
    results['total_input'] = len(input_df)
    
    # Find location column in output
    location_col = [col for col in merged_df.columns if 'location' in col.lower()]
    if not location_col:
        st.error("Could not find 'Location' column in output files")
        return None
    location_col = location_col[0]
    
    # Find address columns in input
    address_cols = [col for col in input_df.columns if 'address' in col.lower()]
    city_cols = [col for col in input_df.columns if 'city' in col.lower()]
    state_cols = [col for col in input_df.columns if 'state' in col.lower()]
    
    if not address_cols or not city_cols or not state_cols:
        st.error("Could not find required address columns in input file")
        return None
    
    address_col = address_cols[0]
    city_col = city_cols[0]
    state_col = state_cols[0]
    
    suite_col = [col for col in input_df.columns if 'suite' in col.lower()]
    suite_col = suite_col[0] if suite_col else None
    
    zip_col = [col for col in input_df.columns if 'zip' in col.lower()]
    zip_col = zip_col[0] if zip_col else None
    
    # Create normalized address set from VALID output (not failed)
    processed_addresses = set()
    for idx, row in valid_df.iterrows():
        if pd.notna(row[location_col]):
            processed_addresses.add(normalize_address(row[location_col]))
    
    # Find missed addresses (not in valid output)
    missed_rows = []
    for idx, row in input_df.iterrows():
        full_address = str(row[address_col]) if pd.notna(row[address_col]) else ""
        
        if suite_col and pd.notna(row[suite_col]):
            full_address += " " + str(row[suite_col])
        
        full_address += " " + (str(row[city_col]) if pd.notna(row[city_col]) else "")
        full_address += " " + (str(row[state_col]) if pd.notna(row[state_col]) else "")
        
        if zip_col and pd.notna(row[zip_col]):
            full_address += " " + str(row[zip_col])
        
        normalized = normalize_address(full_address)
        if normalized not in processed_addresses:
            missed_rows.append(row)
    
    # Add failed records to rerun list by finding their original input rows
    failed_input_rows = []
    for idx, row in failed_df.iterrows():
        if pd.notna(row[location_col]):
            matching_input = get_input_row_from_location(
                row[location_col], 
                input_df, 
                address_col, 
                suite_col, 
                city_col, 
                state_col, 
                zip_col
            )
            if matching_input is not None:
                failed_input_rows.append(matching_input)
    
    # Combine missed addresses and failed addresses for rerun
    all_rerun_rows = missed_rows + failed_input_rows
    
    # Remove duplicates from rerun list
    rerun_df = pd.DataFrame(all_rerun_rows).drop_duplicates()
    
    results['missed_count'] = len(pd.DataFrame(missed_rows))
    results['failed_for_rerun'] = len(failed_input_rows)
    results['total_rerun'] = len(rerun_df)
    
    return {
        'results': results,
        'valid_df': valid_df,
        'rerun_df': rerun_df
    }

# Streamlit UI
st.title("📊 CSV Address Processor")
st.markdown("Merge runs, remove failures, and identify missed addresses")

st.divider()

# Step 1: Upload Output Files
st.subheader("Step 1: Upload Output CSV Files (Multiple Runs)")
output_files = st.file_uploader(
    "Upload your output CSV files",
    type=['csv'],
    accept_multiple_files=True,
    key="output"
)

if output_files:
    st.success(f"✅ {len(output_files)} file(s) uploaded")

st.divider()

# Step 2: Upload Input File
st.subheader("Step 2: Upload Original Input File")
input_file = st.file_uploader(
    "Upload your original input CSV file",
    type=['csv'],
    key="input"
)

if input_file:
    st.success(f"✅ {input_file.name} uploaded")

st.divider()

# Process Button
if st.button("🚀 Process Files", type="primary", use_container_width=True):
    if not output_files:
        st.error("Please upload at least one output CSV file")
    elif not input_file:
        st.error("Please upload the original input file")
    else:
        with st.spinner("Processing files..."):
            try:
                result = process_csv_files(output_files, input_file)
                
                if result:
                    st.success("✅ Processing complete!")
                    
                    # Display metrics
                    col1, col2, col3, col4, col5 = st.columns(5)
                    
                    with col1:
                        st.metric("Total Output Records", result['results']['total_output'])
                    with col2:
                        st.metric("Failed Records", result['results']['failed_removed'])
                    with col3:
                        st.metric("Valid Records", result['results']['valid_records'])
                    with col4:
                        st.metric("Missed Addresses", result['results']['missed_count'])
                    with col5:
                        st.metric("Total for Rerun", result['results']['total_rerun'])
                        
                    st.info(f"ℹ️ Rerun file includes: {result['results']['missed_count']} missed addresses + {result['results']['failed_for_rerun']} failed records")
                    
                    st.divider()
                    
                    # Download buttons
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Merged valid records
                        csv_buffer = io.StringIO()
                        result['valid_df'].to_csv(csv_buffer, index=False)
                        st.download_button(
                            label="⬇️ Download Merged Valid Records",
                            data=csv_buffer.getvalue(),
                            file_name="merged_valid_records.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                    
                    with col2:
                        # Rerun file (missed + failed)
                        if result['results']['total_rerun'] > 0:
                            csv_buffer = io.StringIO()
                            result['rerun_df'].to_csv(csv_buffer, index=False)
                            st.download_button(
                                label="⬇️ Download Addresses for Rerun",
                                data=csv_buffer.getvalue(),
                                file_name="addresses_for_rerun.csv",
                                mime="text/csv",
                                use_container_width=True
                            )
                        else:
                            st.info("No addresses need rerun!")
                    
            except Exception as e:
                st.error(f"Error processing files: {str(e)}")
                st.exception(e)
