import React, { useState, useMemo } from 'react';
import { Search, ChevronUp, ChevronDown } from 'lucide-react';

const Table = ({ tableData }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [sortConfig, setSortConfig] = useState({ key: null, direction: 'asc' });

  if (!tableData || !tableData.columns || !tableData.rows) {
    return null;
  }

  const { title, columns, rows, description } = tableData;

  // Sorting logic
  const sortedRows = useMemo(() => {
    if (!sortConfig.key) return rows;

    const sortedData = [...rows].sort((a, b) => {
      const columnIndex = columns.indexOf(sortConfig.key);
      if (columnIndex === -1) return 0;

      const aValue = a[columnIndex];
      const bValue = b[columnIndex];

      // Handle numeric sorting
      const aNum = parseFloat(aValue);
      const bNum = parseFloat(bValue);
      if (!isNaN(aNum) && !isNaN(bNum)) {
        return sortConfig.direction === 'asc' ? aNum - bNum : bNum - aNum;
      }

      // String sorting
      const aStr = String(aValue).toLowerCase();
      const bStr = String(bValue).toLowerCase();
      
      if (aStr < bStr) return sortConfig.direction === 'asc' ? -1 : 1;
      if (aStr > bStr) return sortConfig.direction === 'asc' ? 1 : -1;
      return 0;
    });

    return sortedData;
  }, [rows, sortConfig, columns]);

  // Search/filter logic
  const filteredRows = useMemo(() => {
    if (!searchTerm) return sortedRows;

    return sortedRows.filter(row =>
      row.some(cell =>
        String(cell).toLowerCase().includes(searchTerm.toLowerCase())
      )
    );
  }, [sortedRows, searchTerm]);

  const handleSort = (column) => {
    setSortConfig(prev => ({
      key: column,
      direction: prev.key === column && prev.direction === 'asc' ? 'desc' : 'asc'
    }));
  };

  const getSortIcon = (column) => {
    if (sortConfig.key !== column) return null;
    return sortConfig.direction === 'asc' ? 
      <ChevronUp size={14} className="inline ml-1" /> : 
      <ChevronDown size={14} className="inline ml-1" />;
  };

  return (
    <div className="table-container">
      {title && <h3 className="table-title">{title}</h3>}
      {description && <p className="table-description">{description}</p>}
      
      {rows.length > 5 && (
        <div className="table-search">
          <Search size={16} className="table-search-icon" />
          <input
            type="text"
            placeholder="Search in table..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="table-search-input"
          />
        </div>
      )}

      <div className="table-wrapper">
        <table className="data-table">
          <thead>
            <tr>
              {columns.map((column, index) => (
                <th 
                  key={index} 
                  onClick={() => handleSort(column)}
                  className="table-header-cell"
                >
                  <div className="table-header-content">
                    {column}
                    {getSortIcon(column)}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filteredRows.length > 0 ? (
              filteredRows.map((row, rowIndex) => (
                <tr key={rowIndex} className="table-row">
                  {row.map((cell, cellIndex) => (
                    <td key={cellIndex} className="table-cell">
                      {cell}
                    </td>
                  ))}
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={columns.length} className="table-empty">
                  No matching results found
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {filteredRows.length > 0 && (
        <div className="table-footer">
          Showing {filteredRows.length} of {rows.length} rows
        </div>
      )}
    </div>
  );
};

export default Table;
