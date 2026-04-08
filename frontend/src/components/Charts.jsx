import React from 'react';
import { Chart as ChartJS, ArcElement, BarElement, CategoryScale, LinearScale, Tooltip, Legend } from 'chart.js';
import { Doughnut, Bar } from 'react-chartjs-2';
import { THEME_COLORS } from '../utils/constants';

// Register all required Chart.js components
ChartJS.register(ArcElement, BarElement, CategoryScale, LinearScale, Tooltip, Legend);

const Charts = ({ inventoryData, isDarkMode }) => {
  // Category Distribution (Doughnut)
  const catMap = {};
  inventoryData.forEach((item) => {
    catMap[item.category] = (catMap[item.category] || 0) + item.quantity;
  });

  const pieData = {
    labels: Object.keys(catMap),
    datasets: [
      {
        data: Object.values(catMap),
        backgroundColor: [
          THEME_COLORS.primary,
          THEME_COLORS.secondary,
          THEME_COLORS.accent,
          THEME_COLORS.emerald,
          THEME_COLORS.amber,
        ],
        borderWidth: 0,
        hoverOffset: 20,
      },
    ],
  };

  const pieOptions = {
    responsive: true,
    maintainAspectRatio: false,
    cutout: '75%',
    plugins: {
      legend: {
        position: 'right',
        labels: {
          color: isDarkMode ? '#94a3b8' : '#1e293b',
          font: { family: 'Plus Jakarta Sans', size: 12 },
        },
      },
    },
  };

  // Top Stocked Items (Bar)
  const sorted = [...inventoryData].sort((a, b) => b.quantity - a.quantity).slice(0, 5);

  const barData = {
    labels: sorted.map((i) =>
      i.description.length > 14 ? i.description.substring(0, 14) + '...' : i.description
    ),
    datasets: [
      {
        data: sorted.map((i) => i.quantity),
        backgroundColor: THEME_COLORS.primary,
        borderRadius: 8,
        barThickness: 25,
      },
    ],
  };

  const barOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      y: {
        grid: { color: isDarkMode ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)' },
        ticks: { color: isDarkMode ? '#64748b' : '#64748b' },
      },
      x: {
        grid: { display: false },
        ticks: { color: isDarkMode ? '#64748b' : '#64748b' },
      },
    },
  };

  return (
    <div className="grid lg:grid-cols-2 gap-6 mb-10">
      <div className="glass p-8 rounded-[2rem]">
        <h3 className="text-lg font-bold mb-6">Distribution by Category</h3>
        <div className="h-64">
          <Doughnut data={pieData} options={pieOptions} />
        </div>
      </div>

      <div className="glass p-8 rounded-[2rem]">
        <h3 className="text-lg font-bold mb-6">Top Stocked Items</h3>
        <div className="h-64">
          <Bar data={barData} options={barOptions} />
        </div>
      </div>
    </div>
  );
};

export default Charts;