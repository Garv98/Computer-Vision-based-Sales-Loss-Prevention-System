import React from 'react';
import { Line, Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend
);

const TrendsPanel = ({ regionId }) => {
  const [period, setPeriod] = React.useState('daily');
  const [trendsData, setTrendsData] = React.useState(null);
  const [isLoading, setIsLoading] = React.useState(false);
  const [error, setError] = React.useState(null);

  React.useEffect(() => {
    if (regionId) {
      fetchTrends();
    }
  }, [regionId, period]);

  const fetchTrends = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(`http://localhost:8000/api/analytics/trends/${period}?region_id=${regionId}`);
      if (!res.ok) throw new Error('Failed to fetch trends');
      const data = await res.json();
      
      if (!data.data || data.data.length === 0) {
        setTrendsData(null);
        setError('No trend data available for this region yet');
        return;
      }
      setTrendsData(data);
    } catch (err) {
      console.error('Error fetching trends:', err);
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) return <div className="panel-card"><div style={{ color: '#888', textAlign: 'center' }}>Loading trends...</div></div>;
  
  if (error) return (
    <div className="panel-card">
      <h3>Historical Trends</h3>
      <div style={{ color: '#888', textAlign: 'center', padding: '20px' }}>{error}</div>
    </div>
  );

  if (!trendsData || !trendsData.data || trendsData.data.length === 0) {
    return (
      <div className="panel-card">
        <h3>Historical Trends</h3>
        <div style={{ color: '#888', textAlign: 'center', padding: '20px' }}>
          No trend data available. Process some videos first.
        </div>
      </div>
    );
  }

  const chartData = {
    labels: trendsData.data.map(d => {
      if (period === 'daily') return d.date || 'N/A';
      if (period === 'weekly') return d.week ? `Week ${d.week.split('T')[0]}` : 'N/A';
      return d.month ? d.month.split('T')[0] : 'N/A';
    }),
    datasets: [
      {
        label: 'Footfall',
        data: trendsData.data.map(d => d.footfall || 0),
        borderColor: 'rgb(75, 192, 192)',
        backgroundColor: 'rgba(75, 192, 192, 0.2)',
        tension: 0.3,
        fill: true,
      },
    ],
  };

  const options = {
    responsive: true,
    plugins: {
      legend: {
        position: 'top',
        labels: { color: '#fff' },
      },
      title: {
        display: true,
        text: `${period.charAt(0).toUpperCase() + period.slice(1)} Footfall Trends`,
        color: '#fff',
      },
    },
    scales: {
      y: {
        ticks: { color: '#fff' },
        grid: { color: 'rgba(255, 255, 255, 0.1)' },
      },
      x: {
        ticks: { color: '#fff' },
        grid: { color: 'rgba(255, 255, 255, 0.1)' },
      },
    },
  };

  return (
    <div className="panel-card">
      <h3>Historical Trends</h3>
      <div style={{ display: 'flex', gap: '10px', marginBottom: '15px' }}>
        <button
          className={period === 'daily' ? '' : 'secondary'}
          onClick={() => setPeriod('daily')}
        >
          Daily
        </button>
        <button
          className={period === 'weekly' ? '' : 'secondary'}
          onClick={() => setPeriod('weekly')}
        >
          Weekly
        </button>
        <button
          className={period === 'monthly' ? '' : 'secondary'}
          onClick={() => setPeriod('monthly')}
        >
          Monthly
        </button>
      </div>
      <div style={{ height: '300px' }}>
        <Line data={chartData} options={options} />
      </div>
    </div>
  );
};

export default TrendsPanel;
