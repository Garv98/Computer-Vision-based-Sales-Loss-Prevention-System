import React, { useState, useEffect } from 'react';
import { Bar, Doughnut } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  ArcElement,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';

ChartJS.register(
  ArcElement,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
);

const AIReportsPanel = ({ regionId, onClose }) => {
  const [report, setReport] = useState(null);
  const [businessInsights, setBusinessInsights] = useState(null);
  const [recentAlerts, setRecentAlerts] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedPeriod, setSelectedPeriod] = useState('daily');

  useEffect(() => {
    fetchAllData();
  }, [regionId, selectedPeriod]);

  const fetchAllData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [reportRes, insightsRes, alertsRes] = await Promise.all([
        regionId ? fetch(`http://localhost:8000/api/ai/generate-report/${regionId}?period=${selectedPeriod}`) : Promise.resolve(null),
        fetch('http://localhost:8000/api/ai/business-insights'),
        fetch(`http://localhost:8000/api/alerts/recent?limit=10${regionId ? `&region_id=${regionId}` : ''}`)
      ]);

      if (reportRes) {
        const reportData = await reportRes.json();
        setReport(reportData.report);
      }

      const insightsData = await insightsRes.json();
      setBusinessInsights(insightsData.insights);

      const alertsData = await alertsRes.json();
      setRecentAlerts(alertsData.alerts || []);
    } catch (err) {
      console.error('Error fetching AI data:', err);
      setError('Failed to load AI insights');
    } finally {
      setIsLoading(false);
    }
  };

  const genderChartData = report?.metrics?.gender_distribution ? {
    labels: Object.keys(report.metrics.gender_distribution),
    datasets: [{
      data: Object.values(report.metrics.gender_distribution),
      backgroundColor: ['#4fc3f7', '#f48fb1', '#a5d6a7'],
      borderWidth: 0,
    }]
  } : null;

  const peakHoursChartData = report?.metrics?.peak_hours ? {
    labels: report.metrics.peak_hours.map(h => `${h.hour}:00`),
    datasets: [{
      label: 'Visitors',
      data: report.metrics.peak_hours.map(h => h.visitors),
      backgroundColor: 'rgba(83, 109, 254, 0.7)',
      borderRadius: 5,
    }]
  } : null;

  if (isLoading) {
    return (
      <div className="panel-card" style={{ minHeight: '400px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center' }}>
          <div className="loading-spinner" style={{ width: '40px', height: '40px', margin: '0 auto 15px' }}></div>
          <p>Generating AI Insights...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="panel-card" style={{ gridColumn: '1 / -1' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h3 style={{ margin: 0 }}>🤖 AI Business Intelligence</h3>
        <div style={{ display: 'flex', gap: '10px' }}>
          <select 
            value={selectedPeriod} 
            onChange={(e) => setSelectedPeriod(e.target.value)}
            style={{ padding: '8px 12px', borderRadius: '6px' }}
          >
            <option value="daily">Daily Report</option>
            <option value="weekly">Weekly Report</option>
            <option value="monthly">Monthly Report</option>
          </select>
          {onClose && (
            <button className="secondary" onClick={onClose}>✕ Close</button>
          )}
        </div>
      </div>

      {error && (
        <div style={{ background: 'rgba(244, 67, 54, 0.1)', padding: '15px', borderRadius: '8px', marginBottom: '20px', color: '#ef5350' }}>
          {error}
        </div>
      )}

      {/* Business Overview Cards */}
      {businessInsights && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '15px', marginBottom: '25px' }}>
          <div style={{ background: 'linear-gradient(135deg, #536dfe 0%, #3d5afe 100%)', padding: '20px', borderRadius: '12px', color: 'white' }}>
            <div style={{ fontSize: '0.85rem', opacity: 0.9, marginBottom: '5px' }}>Today's Footfall</div>
            <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>{businessInsights.today?.footfall || 0}</div>
            <div style={{ fontSize: '0.8rem', marginTop: '5px' }}>
              {businessInsights.today?.trend === 'up' ? '📈' : businessInsights.today?.trend === 'down' ? '📉' : '➡️'}
              {' '}{businessInsights.today?.change_from_yesterday || 0}% from yesterday
            </div>
          </div>
          
          <div style={{ background: 'linear-gradient(135deg, #4caf50 0%, #2e7d32 100%)', padding: '20px', borderRadius: '12px', color: 'white' }}>
            <div style={{ fontSize: '0.85rem', opacity: 0.9, marginBottom: '5px' }}>Weekly Total</div>
            <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>{businessInsights.week?.total_footfall || 0}</div>
            <div style={{ fontSize: '0.8rem', marginTop: '5px' }}>
              ~{businessInsights.week?.daily_average || 0} per day
            </div>
          </div>
          
          <div style={{ background: 'linear-gradient(135deg, #ff9800 0%, #f57c00 100%)', padding: '20px', borderRadius: '12px', color: 'white' }}>
            <div style={{ fontSize: '0.85rem', opacity: 0.9, marginBottom: '5px' }}>Alerts Today</div>
            <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>{businessInsights.alerts_today || 0}</div>
            <div style={{ fontSize: '0.8rem', marginTop: '5px' }}>
              Dwell time alerts
            </div>
          </div>
          
          <div style={{ background: 'linear-gradient(135deg, #9c27b0 0%, #7b1fa2 100%)', padding: '20px', borderRadius: '12px', color: 'white' }}>
            <div style={{ fontSize: '0.85rem', opacity: 0.9, marginBottom: '5px' }}>Busiest Zone</div>
            <div style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>{businessInsights.busiest_region?.name || 'N/A'}</div>
            <div style={{ fontSize: '0.8rem', marginTop: '5px' }}>
              {businessInsights.busiest_region?.visitors || 0} visitors
            </div>
          </div>
        </div>
      )}

      {/* Quick Insights */}
      {businessInsights?.quick_insights && businessInsights.quick_insights.length > 0 && (
        <div style={{ background: 'rgba(83, 109, 254, 0.1)', padding: '15px', borderRadius: '10px', marginBottom: '25px' }}>
          <h4 style={{ margin: '0 0 10px 0', fontSize: '0.95rem' }}>💡 Quick Insights</h4>
          <ul style={{ margin: 0, paddingLeft: '20px' }}>
            {businessInsights.quick_insights.map((insight, i) => (
              <li key={i} style={{ marginBottom: '5px', lineHeight: '1.5' }}>{insight}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Region-specific Report */}
      {report && !report.error && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '25px' }}>
          {/* AI Insights */}
          <div style={{ background: 'rgba(26, 31, 58, 0.5)', padding: '20px', borderRadius: '12px' }}>
            <h4 style={{ margin: '0 0 15px 0' }}>🧠 AI Analysis - {report.region_name}</h4>
            
            <div style={{ marginBottom: '15px' }}>
              <div style={{ fontSize: '0.85rem', color: '#9fa8da', marginBottom: '8px' }}>Key Findings</div>
              {report.ai_insights?.summary?.map((insight, i) => (
                <div key={i} style={{ 
                  background: 'rgba(255,255,255,0.05)', 
                  padding: '10px 15px', 
                  borderRadius: '8px', 
                  marginBottom: '8px',
                  borderLeft: '3px solid #536dfe'
                }}>
                  {insight}
                </div>
              ))}
            </div>
            
            <div>
              <div style={{ fontSize: '0.85rem', color: '#9fa8da', marginBottom: '8px' }}>📋 Recommendations</div>
              {report.ai_insights?.recommendations?.map((rec, i) => (
                <div key={i} style={{ 
                  background: 'rgba(76, 175, 80, 0.1)', 
                  padding: '10px 15px', 
                  borderRadius: '8px', 
                  marginBottom: '8px',
                  borderLeft: '3px solid #4caf50'
                }}>
                  {rec}
                </div>
              ))}
            </div>
            
            {report.ai_insights?.confidence_score && (
              <div style={{ marginTop: '15px', fontSize: '0.8rem', color: '#9fa8da' }}>
                Confidence Score: {Math.round(report.ai_insights.confidence_score)}%
              </div>
            )}
          </div>

          {/* Charts */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {genderChartData && (
              <div style={{ background: 'rgba(26, 31, 58, 0.5)', padding: '20px', borderRadius: '12px' }}>
                <h4 style={{ margin: '0 0 15px 0' }}>👥 Gender Distribution</h4>
                <div style={{ height: '150px' }}>
                  <Doughnut 
                    data={genderChartData} 
                    options={{ 
                      maintainAspectRatio: false,
                      plugins: { 
                        legend: { 
                          position: 'right',
                          labels: { color: '#fff' }
                        } 
                      } 
                    }} 
                  />
                </div>
              </div>
            )}
            
            {peakHoursChartData && (
              <div style={{ background: 'rgba(26, 31, 58, 0.5)', padding: '20px', borderRadius: '12px' }}>
                <h4 style={{ margin: '0 0 15px 0' }}>🕐 Peak Hours</h4>
                <div style={{ height: '150px' }}>
                  <Bar 
                    data={peakHoursChartData} 
                    options={{ 
                      maintainAspectRatio: false,
                      plugins: { legend: { display: false } },
                      scales: {
                        y: { ticks: { color: '#fff' }, grid: { color: 'rgba(255,255,255,0.1)' } },
                        x: { ticks: { color: '#fff' }, grid: { display: false } }
                      }
                    }} 
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Recent Alerts */}
      {recentAlerts.length > 0 && (
        <div style={{ background: 'rgba(26, 31, 58, 0.5)', padding: '20px', borderRadius: '12px' }}>
          <h4 style={{ margin: '0 0 15px 0' }}>🚨 Recent Alerts</h4>
          <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
            <table className="analytics-table" style={{ width: '100%' }}>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Type</th>
                  <th>Region</th>
                </tr>
              </thead>
              <tbody>
                {recentAlerts.map((alert, i) => (
                  <tr key={i}>
                    <td>{new Date(alert.time).toLocaleString()}</td>
                    <td>
                      <span className="badge badge-warning">{alert.type}</span>
                    </td>
                    <td>{alert.region_name || `Region ${alert.region_id}`}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {!regionId && (
        <div style={{ textAlign: 'center', color: '#9fa8da', padding: '20px' }}>
          <p>Select a region to see detailed AI analysis and recommendations.</p>
        </div>
      )}
    </div>
  );
};

export default AIReportsPanel;
