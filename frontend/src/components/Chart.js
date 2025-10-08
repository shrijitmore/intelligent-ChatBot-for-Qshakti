import React from 'react';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell
} from 'recharts';

const COLORS = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40'];

const Chart = ({ chartData }) => {
  if (!chartData || !chartData.type || !chartData.data) {
    return null;
  }

  const { type, title, data } = chartData;

  // Transform data for recharts format
  const transformDataForRecharts = () => {
    if (!data.labels || !data.datasets || data.datasets.length === 0) {
      return [];
    }

    // For bar, line, and scatter charts
    if (type === 'bar' || type === 'line' || type === 'scatter' || type === 'histogram') {
      return data.labels.map((label, index) => {
        const point = { name: label };
        data.datasets.forEach((dataset) => {
          point[dataset.label || 'value'] = dataset.data[index];
        });
        return point;
      });
    }

    // For pie chart
    if (type === 'pie') {
      return data.labels.map((label, index) => ({
        name: label,
        value: data.datasets[0].data[index]
      }));
    }

    return [];
  };

  const chartDataFormatted = transformDataForRecharts();

  const renderChart = () => {
    switch (type.toLowerCase()) {
      case 'bar':
      case 'histogram':
        return (
          <ResponsiveContainer width="100%" height={350}>
            <BarChart data={chartDataFormatted}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
              <XAxis dataKey="name" stroke="#666" />
              <YAxis stroke="#666" />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: '#fff', 
                  border: '1px solid #ccc',
                  borderRadius: '8px'
                }} 
              />
              <Legend />
              {data.datasets.map((dataset, index) => (
                <Bar
                  key={index}
                  dataKey={dataset.label || 'value'}
                  fill={dataset.backgroundColor?.[0] || COLORS[index % COLORS.length]}
                />
              ))}
            </BarChart>
          </ResponsiveContainer>
        );

      case 'line':
        return (
          <ResponsiveContainer width="100%" height={350}>
            <LineChart data={chartDataFormatted}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
              <XAxis dataKey="name" stroke="#666" />
              <YAxis stroke="#666" />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: '#fff', 
                  border: '1px solid #ccc',
                  borderRadius: '8px'
                }} 
              />
              <Legend />
              {data.datasets.map((dataset, index) => (
                <Line
                  key={index}
                  type="monotone"
                  dataKey={dataset.label || 'value'}
                  stroke={dataset.backgroundColor?.[0] || COLORS[index % COLORS.length]}
                  strokeWidth={2}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        );

      case 'pie':
        return (
          <ResponsiveContainer width="100%" height={350}>
            <PieChart>
              <Pie
                data={chartDataFormatted}
                cx="50%"
                cy="50%"
                labelLine={true}
                label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                outerRadius={120}
                fill="#8884d8"
                dataKey="value"
              >
                {chartDataFormatted.map((entry, index) => (
                  <Cell 
                    key={`cell-${index}`} 
                    fill={data.datasets[0]?.backgroundColor?.[index] || COLORS[index % COLORS.length]} 
                  />
                ))}
              </Pie>
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: '#fff', 
                  border: '1px solid #ccc',
                  borderRadius: '8px'
                }} 
              />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        );

      case 'scatter':
        return (
          <ResponsiveContainer width="100%" height={350}>
            <ScatterChart>
              <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
              <XAxis dataKey="name" stroke="#666" />
              <YAxis stroke="#666" />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: '#fff', 
                  border: '1px solid #ccc',
                  borderRadius: '8px'
                }} 
              />
              <Legend />
              {data.datasets.map((dataset, index) => (
                <Scatter
                  key={index}
                  name={dataset.label || 'value'}
                  data={chartDataFormatted}
                  fill={dataset.backgroundColor?.[0] || COLORS[index % COLORS.length]}
                />
              ))}
            </ScatterChart>
          </ResponsiveContainer>
        );

      default:
        return (
          <div className="chart-error">
            <p>Unsupported chart type: {type}</p>
          </div>
        );
    }
  };

  return (
    <div className="chart-container">
      {title && <h3 className="chart-title">{title}</h3>}
      <div className="chart-wrapper">
        {renderChart()}
      </div>
    </div>
  );
};

export default Chart;
