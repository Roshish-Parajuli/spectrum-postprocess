import streamlit as st
import pandas as pd
import io
import re

st.set_page_config(page_title="CSV Data Processor", page_icon="📊", layout="wide")

def normalize_address(addr):
    """Normalize address for comparison"""
    if pd.isna(addr):
        return ""
    addr = str(addr).upper()
    addr = re.sub(r'\s+', ' ', addr)
    addr = re.sub(r'[.,#-]', '', addr)
    return addr.strip()

def create_full_address_vectorized(df, address_col, suite_col, city_col, state_col, zip_col):
    """Create full address strings for entire dataframe at once"""
    parts = []
    
    # Address
    parts.append(df[address_col].fillna('').astype(str))
    
    # Suite
    if suite_col:
        parts.append(df[suite_col].fillna('').astype(str))
    
    # City
    parts.append(df[city_col].fillna('').astype(str))
    
    # State
    parts.append(df[state_col].fillna('').astype(str))
    
    # Zip
    if zip_col:
        parts.append(df[zip_col].fillna('').astype(str))
    
    # Join all parts with space
    full_addresses = parts[0]
    for part in parts[1:]:
        full_addresses = full_addresses + ' ' + part
    
    # Normalize all addresses
    return full_addresses.apply(normalize_address)

def process_csv_files(output_files, input_file):
    """Main processing logic"""
    results = {}
    
    # Step 1: Combine multiple CSV files
    with st.spinner("📁 Reading and merging output files..."):
        all_dfs = []
        for file in output_files:
            df = pd.read_csv(file)
            all_dfs.append(df)
        
        merged_df = pd.concat(all_dfs, ignore_index=True)
        results['total_output'] = len(merged_df)
    
    # Step 2: Separate failed and valid records
    with st.spinner("🔍 Identifying failed records..."):
        remarks_col = [col for col in merged_df.columns if 'remark' in col.lower()]
        
        if remarks_col:
            remarks_col = remarks_col[0]
            st.info(f"📋 Found Remarks column: **{remarks_col}**")
            
            # Consider both "failed" and "api error" as failures
            remarks_series = merged_df[remarks_col].fillna('').astype(str)
            
            failed_mask = (
                remarks_series.str.contains('failed', case=False, regex=False) |
                remarks_series.str.contains('api error', case=False, regex=False)
            )
            
            failed_df = merged_df[failed_mask].copy()
            valid_df = merged_df[~failed_mask].copy()
            
            st.info(f"🔍 Found **{failed_mask.sum()}** records with 'failed' or 'API Error'")
        else:
            st.warning("⚠️ Could not find 'Remarks' column in output files")
            failed_df = pd.DataFrame()
            valid_df = merged_df.copy()
        
        results['failed_removed'] = len(failed_df)
        results['valid_records'] = len(valid_df)
    
    # Step 3: Parse input file
    with st.spinner("📂 Reading input file..."):
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
    
    # Create normalized addresses for ALL records at once (vectorized)
    with st.spinner("🔄 Creating normalized addresses..."):
        # For valid output
        valid_df['normalized_addr'] = valid_df[location_col].fillna('').astype(str).apply(normalize_address)
        processed_addresses = set(valid_df['normalized_addr'].unique())
        
        # For input
        input_df['normalized_addr'] = create_full_address_vectorized(
            input_df, address_col, suite_col, city_col, state_col, zip_col
        )
        
        # For failed output (to match back to input)
        if len(failed_df) > 0:
            failed_df['normalized_addr'] = failed_df[location_col].fillna('').astype(str).apply(normalize_address)
    
    # Find missed addresses (vectorized comparison)
    with st.spinner("📊 Finding missed addresses..."):
        missed_mask = ~input_df['normalized_addr'].isin(processed_addresses)
        missed_df = input_df[missed_mask].copy()
        results['missed_count'] = len(missed_df)
    
    # Find failed addresses that exist in input (vectorized merge)
    with st.spinner("⚠️ Processing failed records..."):
        if len(failed_df) > 0:
            # Merge failed records with input to get original rows
            failed_input_df = input_df[input_df['normalized_addr'].isin(failed_df['normalized_addr'])].copy()
            results['failed_for_rerun'] = len(failed_input_df)
        else:
            failed_input_df = pd.DataFrame()
            results['failed_for_rerun'] = 0
    
    # Combine missed and failed for rerun (vectorized concat + drop_duplicates)
    with st.spinner("📋 Creating rerun list..."):
        if len(failed_input_df) > 0:
            rerun_df = pd.concat([missed_df, failed_input_df], ignore_index=True)
        else:
            rerun_df = missed_df.copy()
        
        # Remove the temporary normalized_addr column before output
        if 'normalized_addr' in rerun_df.columns:
            rerun_df = rerun_df.drop(columns=['normalized_addr'])
        
        # Remove duplicates
        rerun_df = rerun_df.drop_duplicates()
        results['total_rerun'] = len(rerun_df)
    
    # Clean up temporary columns
    if 'normalized_addr' in valid_df.columns:
        valid_df = valid_df.drop(columns=['normalized_addr'])
    if 'normalized_addr' in failed_df.columns:
        failed_df = failed_df.drop(columns=['normalized_addr'])
    
    return {
        'results': results,
        'valid_df': valid_df,
        'failed_df': failed_df,
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
                
                # Preview failed records
                if len(result['failed_df']) > 0:
                    with st.expander(f"🔍 Preview Failed Records ({len(result['failed_df'])} records)"):
                        st.dataframe(result['failed_df'].head(20), use_container_width=True)
                
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
