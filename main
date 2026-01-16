import React, { useState } from 'react';
import { Upload, Download, AlertCircle, CheckCircle, FileText } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';

const CSVProcessor = () => {
  const [outputFiles, setOutputFiles] = useState([]);
  const [inputFile, setInputFile] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState('');

  const parseCSV = (text) => {
    const lines = text.split('\n').filter(line => line.trim());
    if (lines.length === 0) return { headers: [], rows: [] };
    
    const headers = lines[0].split(',').map(h => h.trim().replace(/^"|"$/g, ''));
    const rows = lines.slice(1).map(line => {
      const values = [];
      let current = '';
      let inQuotes = false;
      
      for (let i = 0; i < line.length; i++) {
        const char = line[i];
        if (char === '"') {
          inQuotes = !inQuotes;
        } else if (char === ',' && !inQuotes) {
          values.push(current.trim().replace(/^"|"$/g, ''));
          current = '';
        } else {
          current += char;
        }
      }
      values.push(current.trim().replace(/^"|"$/g, ''));
      
      const row = {};
      headers.forEach((header, idx) => {
        row[header] = values[idx] || '';
      });
      return row;
    });
    
    return { headers, rows };
  };

  const normalizeAddress = (addr) => {
    return addr.toUpperCase()
      .replace(/\s+/g, ' ')
      .replace(/[.,#-]/g, '')
      .trim();
  };

  const processFiles = async () => {
    setProcessing(true);
    setError('');
    setResults(null);

    try {
      if (outputFiles.length === 0) {
        throw new Error('Please upload at least one output CSV file');
      }
      if (!inputFile) {
        throw new Error('Please upload the original input file');
      }

      // Step 1: Combine multiple CSV files
      let allRows = [];
      let headers = [];
      
      for (const file of outputFiles) {
        const text = await file.text();
        const parsed = parseCSV(text);
        if (headers.length === 0) {
          headers = parsed.headers;
        }
        allRows = allRows.concat(parsed.rows);
      }

      // Step 2: Remove rows with "failed" in remarks column
      const remarksCol = headers.find(h => h.toLowerCase().includes('remark'));
      const validRows = allRows.filter(row => {
        const remarks = remarksCol ? row[remarksCol] : '';
        return !remarks.toLowerCase().includes('failed');
      });

      // Step 3: Parse input file
      const inputText = await inputFile.text();
      const inputData = parseCSV(inputText);
      
      // Find location column in output
      const locationCol = headers.find(h => h.toLowerCase().includes('location'));
      if (!locationCol) {
        throw new Error('Could not find "Location" column in output files');
      }

      // Find address columns in input
      const addressCol = inputData.headers.find(h => h.toLowerCase().includes('address'));
      const suiteCol = inputData.headers.find(h => h.toLowerCase().includes('suite'));
      const cityCol = inputData.headers.find(h => h.toLowerCase().includes('city'));
      const stateCol = inputData.headers.find(h => h.toLowerCase().includes('state'));
      const zipCol = inputData.headers.find(h => h.toLowerCase().includes('zip'));

      if (!addressCol || !cityCol || !stateCol) {
        throw new Error('Could not find required address columns in input file');
      }

      // Create normalized address map from output
      const processedAddresses = new Set();
      validRows.forEach(row => {
        if (row[locationCol]) {
          processedAddresses.add(normalizeAddress(row[locationCol]));
        }
      });

      // Find missed addresses
      const missedRows = [];
      inputData.rows.forEach(row => {
        let fullAddress = row[addressCol] || '';
        if (suiteCol && row[suiteCol]) {
          fullAddress += ' ' + row[suiteCol];
        }
        fullAddress += ' ' + (row[cityCol] || '');
        fullAddress += ' ' + (row[stateCol] || '');
        if (zipCol && row[zipCol]) {
          fullAddress += ' ' + row[zipCol];
        }

        const normalized = normalizeAddress(fullAddress);
        if (!processedAddresses.has(normalized)) {
          missedRows.push(row);
        }
      });

      // Step 4: Create downloadable files
      const createCSV = (headers, rows) => {
        const csvContent = [
          headers.join(','),
          ...rows.map(row => 
            headers.map(h => {
              const val = row[h] || '';
              return val.includes(',') ? `"${val}"` : val;
            }).join(',')
          )
        ].join('\n');
        return csvContent;
      };

      const mergedCSV = createCSV(headers, validRows);
      const missedCSV = createCSV(inputData.headers, missedRows);

      setResults({
        totalOutput: allRows.length,
        failedRemoved: allRows.length - validRows.length,
        validRecords: validRows.length,
        totalInput: inputData.rows.length,
        missedCount: missedRows.length,
        mergedCSV,
        missedCSV,
        mergedFilename: 'merged_valid_records.csv',
        missedFilename: 'missed_addresses_rerun.csv'
      });

    } catch (err) {
      setError(err.message);
    } finally {
      setProcessing(false);
    }
  };

  const downloadFile = (content, filename) => {
    const blob = new Blob([content], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-8">
      <div className="max-w-4xl mx-auto">
        <div className="bg-white rounded-lg shadow-xl p-8">
          <h1 className="text-3xl font-bold text-gray-800 mb-2">CSV Address Processor</h1>
          <p className="text-gray-600 mb-6">Merge runs, remove failures, and identify missed addresses</p>

          {/* Step 1: Upload Output Files */}
          <div className="mb-6">
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Step 1: Upload Output CSV Files (Multiple Runs)
            </label>
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-indigo-500 transition-colors">
              <Upload className="mx-auto h-12 w-12 text-gray-400 mb-2" />
              <input
                type="file"
                multiple
                accept=".csv"
                onChange={(e) => setOutputFiles(Array.from(e.target.files))}
                className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100"
              />
              {outputFiles.length > 0 && (
                <p className="mt-2 text-sm text-green-600">
                  {outputFiles.length} file(s) selected
                </p>
              )}
            </div>
          </div>

          {/* Step 2: Upload Input File */}
          <div className="mb-6">
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Step 2: Upload Original Input File
            </label>
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-indigo-500 transition-colors">
              <Upload className="mx-auto h-12 w-12 text-gray-400 mb-2" />
              <input
                type="file"
                accept=".csv"
                onChange={(e) => setInputFile(e.target.files[0])}
                className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100"
              />
              {inputFile && (
                <p className="mt-2 text-sm text-green-600">
                  {inputFile.name}
                </p>
              )}
            </div>
          </div>

          {/* Process Button */}
          <button
            onClick={processFiles}
            disabled={processing || outputFiles.length === 0 || !inputFile}
            className="w-full bg-indigo-600 text-white py-3 px-6 rounded-lg font-semibold hover:bg-indigo-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors mb-6"
          >
            {processing ? 'Processing...' : 'Process Files'}
          </button>

          {/* Error Display */}
          {error && (
            <Alert className="mb-6 bg-red-50 border-red-200">
              <AlertCircle className="h-4 w-4 text-red-600" />
              <AlertDescription className="text-red-800">{error}</AlertDescription>
            </Alert>
          )}

          {/* Results */}
          {results && (
            <div className="space-y-6">
              <Alert className="bg-green-50 border-green-200">
                <CheckCircle className="h-4 w-4 text-green-600" />
                <AlertDescription className="text-green-800">
                  Processing complete!
                </AlertDescription>
              </Alert>

              <div className="grid grid-cols-2 gap-4">
                <div className="bg-blue-50 p-4 rounded-lg">
                  <p className="text-sm text-gray-600">Total Output Records</p>
                  <p className="text-2xl font-bold text-blue-700">{results.totalOutput}</p>
                </div>
                <div className="bg-red-50 p-4 rounded-lg">
                  <p className="text-sm text-gray-600">Failed Records Removed</p>
                  <p className="text-2xl font-bold text-red-700">{results.failedRemoved}</p>
                </div>
                <div className="bg-green-50 p-4 rounded-lg">
                  <p className="text-sm text-gray-600">Valid Records</p>
                  <p className="text-2xl font-bold text-green-700">{results.validRecords}</p>
                </div>
                <div className="bg-orange-50 p-4 rounded-lg">
                  <p className="text-sm text-gray-600">Missed Addresses</p>
                  <p className="text-2xl font-bold text-orange-700">{results.missedCount}</p>
                </div>
              </div>

              <div className="space-y-3">
                <button
                  onClick={() => downloadFile(results.mergedCSV, results.mergedFilename)}
                  className="w-full bg-green-600 text-white py-3 px-6 rounded-lg font-semibold hover:bg-green-700 transition-colors flex items-center justify-center gap-2"
                >
                  <Download className="h-5 w-5" />
                  Download Merged Valid Records
                </button>
                
                {results.missedCount > 0 && (
                  <button
                    onClick={() => downloadFile(results.missedCSV, results.missedFilename)}
                    className="w-full bg-orange-600 text-white py-3 px-6 rounded-lg font-semibold hover:bg-orange-700 transition-colors flex items-center justify-center gap-2"
                  >
                    <FileText className="h-5 w-5" />
                    Download Missed Addresses for Rerun
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default CSVProcessor;
