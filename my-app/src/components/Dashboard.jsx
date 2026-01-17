import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import TrendsPanel from './TrendsPanel';
import HeatmapVisualization from './HeatmapVisualization';
import AIReportsPanel from './AIReportsPanel';

const API_URL = 'http://localhost:8000/api';

function Dashboard({ setIsAuthenticated }) {
  const navigate = useNavigate();
  const [userRole, setUserRole] = useState('staff');
  const [userName, setUserName] = useState('');
  
  // --- State ---
  const [cameras, setCameras] = useState([]);
  const [selectedCamId, setSelectedCamId] = useState('');
  const [newCamId, setNewCamId] = useState('');
  const [newCamName, setNewCamName] = useState('');
  
  const [videoSource, setVideoSource] = useState(null); // For annotation (upload/stream)
  const [videoFilePath, setVideoFilePath] = useState('');
  const [inputType, setInputType] = useState('upload');
  const [streamUrl, setStreamUrl] = useState('');

  // Annotation
  const [isDrawing, setIsDrawing] = useState(false);
  const [startPos, setStartPos] = useState({ x: 0, y: 0 });
  const [currentRect, setCurrentRect] = useState(null);
  const [regionName, setRegionName] = useState('');
  const [alertThreshold, setAlertThreshold] = useState(5);
  
  // Data
  const [regions, setRegions] = useState([]);
  const [selectedRegionId, setSelectedRegionId] = useState('');
  const [showTrends, setShowTrends] = useState(false);
  const [showAIReports, setShowAIReports] = useState(false);
  const [analyticsData, setAnalyticsData] = useState(null);
  const [demographicsData, setDemographicsData] = useState(null);
  const [trackingStats, setTrackingStats] = useState(null);
  const [dateFilter, setDateFilter] = useState('');
  
  // Playback
  const [cameraShards, setCameraShards] = useState([]);
  const [currentShardIndex, setCurrentShardIndex] = useState(0);
  const [isPlayingAll, setIsPlayingAll] = useState(false);
  const [currentVideoUrl, setCurrentVideoUrl] = useState('');
  const [videoScale, setVideoScale] = useState({ x: 1, y: 1, offsetX: 0, offsetY: 0 });
  const [liveScale, setLiveScale] = useState({ x: 1, y: 1, offsetX: 0, offsetY: 0 });

  const videoRef = useRef(null);
  const liveImgRef = useRef(null);
  const canvasRef = useRef(null);
  const playbackRef = useRef(null);

  // --- Effects ---
  useEffect(() => {
    // Get user role from localStorage
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    setUserRole(user.role || 'staff');
    setUserName(user.fullName || user.email || 'User');
    
    fetchCameras();
    fetchRegions();

    const handleResize = () => {
      // Update Playback Scale
      if (playbackRef.current) {
        const video = playbackRef.current;
        if (video.videoWidth) {
          const containerWidth = video.clientWidth;
          const containerHeight = video.clientHeight;
          const videoAspect = video.videoWidth / video.videoHeight;
          const containerAspect = containerWidth / containerHeight;
          
          let displayWidth, displayHeight, offsetX, offsetY;
          
          if (videoAspect > containerAspect) {
            displayWidth = containerWidth;
            displayHeight = containerWidth / videoAspect;
            offsetX = 0;
            offsetY = (containerHeight - displayHeight) / 2;
          } else {
            displayHeight = containerHeight;
            displayWidth = containerHeight * videoAspect;
            offsetX = (containerWidth - displayWidth) / 2;
            offsetY = 0;
          }
          
          setVideoScale({
            x: displayWidth / video.videoWidth,
            y: displayHeight / video.videoHeight,
            offsetX: offsetX,
            offsetY: offsetY
          });
        }
      }
      // Update Annotation Canvas
      if (videoRef.current && canvasRef.current) {
        canvasRef.current.width = videoRef.current.clientWidth;
        canvasRef.current.height = videoRef.current.clientHeight;
      }
      // Update Live Scale
      if (liveImgRef.current) {
        const img = liveImgRef.current;
        if (img.naturalWidth) {
          const containerWidth = img.clientWidth;
          const containerHeight = img.clientHeight;
          const imgAspect = img.naturalWidth / img.naturalHeight;
          const containerAspect = containerWidth / containerHeight;
          
          let displayWidth, displayHeight, offsetX, offsetY;
          
          if (imgAspect > containerAspect) {
            displayWidth = containerWidth;
            displayHeight = containerWidth / imgAspect;
            offsetX = 0;
            offsetY = (containerHeight - displayHeight) / 2;
          } else {
            displayHeight = containerHeight;
            displayWidth = containerHeight * imgAspect;
            offsetX = (containerWidth - displayWidth) / 2;
            offsetY = 0;
          }
          
          setLiveScale({
            x: displayWidth / img.naturalWidth,
            y: displayHeight / img.naturalHeight,
            offsetX: offsetX,
            offsetY: offsetY
          });
        }
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  useEffect(() => {
    if (selectedCamId) {
      const camIdInt = parseInt(selectedCamId);
      if (!isNaN(camIdInt)) {
        fetchShards(camIdInt);
      }
    }
  }, [selectedCamId]);

  // Seamless Playback Logic
  useEffect(() => {
    if (isPlayingAll && cameraShards.length > 0) {
      if (currentShardIndex < cameraShards.length) {
        const shardId = cameraShards[currentShardIndex];
        setCurrentVideoUrl(`http://localhost:8000/shards/${shardId}.mp4`);
      } else {
        setIsPlayingAll(false); // End of playlist
      }
    }
  }, [currentShardIndex, isPlayingAll, cameraShards]);

  // --- API Calls ---
  const fetchCameras = async () => {
    try {
      const res = await axios.get(`${API_URL}/cameras`);
      setCameras(res.data);
    } catch (err) { console.error(err); }
  };

  const fetchShards = async (camId) => {
    try {
      const res = await axios.get(`${API_URL}/shards/${camId}`);
      setCameraShards(res.data.shards);
      // Reset playback when camera changes
      setCurrentShardIndex(0);
      setIsPlayingAll(false);
      if (res.data.shards.length > 0) {
        setCurrentVideoUrl(`http://localhost:8000/shards/${res.data.shards[0]}.mp4`);
      } else {
        setCurrentVideoUrl('');
      }
    } catch (err) { console.error(err); }
  };

  const fetchRegions = async () => {
    try {
      const res = await axios.get(`${API_URL}/regions`);
      setRegions(res.data);
    } catch (err) { console.error(err); }
  };

  const fetchAnalytics = async (regionId) => {
    if (!regionId) return;
    setSelectedRegionId(regionId);
    try {
      const [footfallRes, timeRes, demoRes, trackRes] = await Promise.all([
        axios.get(`${API_URL}/analytics/footfall/${regionId}`),
        axios.get(`${API_URL}/analytics/timespent/${regionId}`),
        axios.get(`${API_URL}/analytics/demographics/${regionId}`),
        axios.get(`${API_URL}/analytics/tracking-stats/${regionId}`)
      ]);
      
      const combined = {};
      footfallRes.data.footfall.forEach(([shardId, count]) => {
        if (!combined[shardId]) combined[shardId] = { shardId, footfall: 0, timeSpent: 0 };
        combined[shardId].footfall = count;
      });
      timeRes.data.data.forEach(([shardId, time]) => {
        if (!combined[shardId]) combined[shardId] = { shardId, footfall: 0, timeSpent: 0 };
        combined[shardId].timeSpent = time;
      });
      setAnalyticsData(Object.values(combined));
      setDemographicsData(demoRes.data.data);
      setTrackingStats(trackRes.data.data);
    } catch (err) { console.error(err); }
  };

  // --- Handlers ---
  const handleAddCamera = async () => {
    try {
      await axios.post(`${API_URL}/cameras`, { cam_id: parseInt(newCamId), cam_name: newCamName });
      fetchCameras();
      setNewCamId(''); setNewCamName('');
    } catch (err) { alert("Error adding camera"); }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await axios.post(`${API_URL}/upload`, formData, { headers: { 'Content-Type': 'multipart/form-data' } });
      setVideoFilePath(res.data.file_path);
      setVideoSource(URL.createObjectURL(file));
    } catch (err) { alert("Upload failed"); }
  };

  const [isProcessing, setIsProcessing] = useState(false);
  const [liveFrame, setLiveFrame] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const wsRef = useRef(null);

  const handleStartProcessing = async () => {
    if (!selectedCamId || (!videoFilePath && !streamUrl)) {
      alert("Select camera and source"); return;
    }
    
    setIsProcessing(true);
    
    // Close existing WS if any
    if (wsRef.current) wsRef.current.close();

    const ws = new WebSocket('ws://localhost:8000/ws/process');
    wsRef.current = ws;

    ws.onopen = () => {
      console.log("WS Connected");
      ws.send(JSON.stringify({
        source: inputType === 'upload' ? videoFilePath : streamUrl,
        cam_id: parseInt(selectedCamId),
        shard_duration: 30,
        alert_threshold: alertThreshold
      }));
    };

    ws.onmessage = (event) => {
      // If binary, it's a frame
      if (event.data instanceof Blob) {
        const url = URL.createObjectURL(event.data);
        setLiveFrame(prev => {
          // Revoke previous blob URL to prevent memory leak
          if (prev && prev.startsWith('blob:')) {
            URL.revokeObjectURL(prev);
          }
          return url;
        });
      } else {
        // JSON status
        try {
          const data = JSON.parse(event.data);
          if (data.status === 'completed') {
            alert("Processing Completed!");
            setIsProcessing(false);
            fetchShards(parseInt(selectedCamId));
            // Clean up live frame
            setLiveFrame(prev => {
              if (prev && prev.startsWith('blob:')) {
                URL.revokeObjectURL(prev);
              }
              return null;
            });
          } else if (data.type === 'alert') {
            setAlerts(prev => [data, ...prev].slice(0, 5));
          }
        } catch (e) {}
      }
    };

    ws.onclose = () => {
      console.log("WS Closed");
      setIsProcessing(false);
      // Clean up live frame on close
      setLiveFrame(prev => {
        if (prev && prev.startsWith('blob:')) {
          URL.revokeObjectURL(prev);
        }
        return null;
      });
    };

    ws.onerror = (err) => {
      console.error("WS Error", err);
      setIsProcessing(false);
    };
  };

  const handleStopProcessing = () => {
    if (wsRef.current) {
      wsRef.current.close();
      setIsProcessing(false);
      // Clean up live frame
      setLiveFrame(prev => {
        if (prev && prev.startsWith('blob:')) {
          URL.revokeObjectURL(prev);
        }
        return null;
      });
    }
  };

  const handleSaveRegion = async () => {
    if (!currentRect || !selectedCamId || !regionName) {
      alert("Missing info"); return;
    }
    
    // Calculate scaling factors
    let scaleX = 1;
    let scaleY = 1;
    
    if (videoRef.current) {
      const vid = videoRef.current;
      if (vid.videoWidth && vid.clientWidth) {
        scaleX = vid.videoWidth / vid.clientWidth;
        scaleY = vid.videoHeight / vid.clientHeight;
      }
    }

    let { x, y, w, h } = currentRect;
    
    // Scale to intrinsic video resolution
    let x1 = x * scaleX;
    let x2 = (x + w) * scaleX;
    let y1 = y * scaleY;
    let y2 = (y + h) * scaleY;

    if (x1 > x2) [x1, x2] = [x2, x1];
    if (y1 > y2) [y1, y2] = [y2, y1];

    try {
      await axios.post(`${API_URL}/regions`, {
        region_id: Math.floor(Math.random() * 1000000),
        region_name: regionName,
        x1: Math.round(x1), x2: Math.round(x2), y1: Math.round(y1), y2: Math.round(y2),
        cam_id: parseInt(selectedCamId)
      });
      alert("Region saved!");
      setRegionName('');
      fetchRegions();
    } catch (err) { alert("Error saving region"); }
  };

  const handleResetDatabase = async () => {
    if (window.confirm("Are you sure you want to delete ALL data? This cannot be undone.")) {
      try {
        await axios.delete(`${API_URL}/reset-database`);
        alert("Database reset successfully.");
        // Refresh state
        setCameras([]);
        setRegions([]);
        setCameraShards([]);
        setAnalyticsData(null);
        setSelectedCamId('');
        fetchCameras();
      } catch (err) {
        alert("Error resetting database");
        console.error(err);
      }
    }
  };

  // --- Drawing Logic ---
  const handleMouseDown = (e) => {
    const rect = canvasRef.current.getBoundingClientRect();
    setStartPos({ x: e.clientX - rect.left, y: e.clientY - rect.top });
    setIsDrawing(true);
  };
  const handleMouseMove = (e) => {
    if (!isDrawing) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const w = (e.clientX - rect.left) - startPos.x;
    const h = (e.clientY - rect.top) - startPos.y;
    setCurrentRect({ x: startPos.x, y: startPos.y, w, h });
    const ctx = canvasRef.current.getContext('2d');
    ctx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);
    ctx.strokeStyle = '#007acc'; ctx.lineWidth = 2; ctx.strokeRect(startPos.x, startPos.y, w, h);
  };
  const handleMouseUp = () => setIsDrawing(false);

  const handleDismissAlert = (index) => {
    setAlerts(prev => prev.filter((_, i) => i !== index));
  };

  const handleLogout = () => {
    setIsAuthenticated(false);
    localStorage.removeItem('isAuthenticated');
    localStorage.removeItem('user');
    navigate('/login');
  };

  const handleExportCSV = async () => {
    if (!selectedRegionId) {
      alert('Please select a region first');
      return;
    }
    try {
      const response = await fetch(`http://localhost:8000/export/analytics/csv/${selectedRegionId}`);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `analytics_region_${selectedRegionId}_${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert('Export failed');
      console.error(err);
    }
  };

  // --- Render ---
  return (
    <div className="dashboard-container">
      {/* Global Alert Container */}
      <div style={{
        position: 'fixed', 
        top: '20px', 
        right: '20px', 
        zIndex: 9999, 
        display: 'flex', 
        flexDirection: 'column', 
        gap: '10px', 
        width: '300px'
      }}>
        {alerts.map((alert, idx) => (
          <div key={idx} style={{
            backgroundColor: '#dc3545', 
            color: 'white', 
            padding: '15px', 
            borderRadius: '8px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
            fontSize: '14px',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '10px',
            animation: 'fadeIn 0.3s ease-in-out',
            position: 'relative'
          }}>
            <span style={{fontSize: '20px'}}>⚠️</span>
            <div style={{flex: 1}}>
              <div style={{fontWeight: 'bold', marginBottom: '4px'}}>Alert</div>
              <div>{alert.message}</div>
            </div>
            <button 
              onClick={() => handleDismissAlert(idx)}
              style={{
                background: 'transparent',
                border: 'none',
                color: 'white',
                fontSize: '16px',
                cursor: 'pointer',
                padding: '0 5px',
                lineHeight: 1,
                opacity: 0.8
              }}
            >
              ✕
            </button>
          </div>
        ))}
      </div>

      {/* Sidebar */}
      <div className="sidebar">
        <div className="sidebar-header">
          <div>VisionGuard</div>
          <div style={{ fontSize: '12px', marginTop: '5px', opacity: 0.8 }}>
            {userName} ({userRole})
          </div>
        </div>
        
        <div className="sidebar-section">
          <h4>Cameras</h4>
          {cameras.map(cam => (
            <div 
              key={cam.cam_id} 
              className={`list-item ${parseInt(selectedCamId) === cam.cam_id ? 'active' : ''}`}
              onClick={() => setSelectedCamId(cam.cam_id)}
            >
              <span>{cam.cam_name}</span>
              <small>ID: {cam.cam_id}</small>
            </div>
          ))}
          <div style={{ marginTop: '10px' }}>
            <input placeholder="New ID" type="number" value={newCamId} onChange={e => setNewCamId(e.target.value)} style={{marginBottom: '5px'}}/>
            <input placeholder="New Name" value={newCamName} onChange={e => setNewCamName(e.target.value)} style={{marginBottom: '5px'}}/>
            <button onClick={handleAddCamera} className="secondary" style={{fontSize: '0.8rem'}}>+ Add Camera</button>
          </div>
        </div>

        <div className="sidebar-section">
          <h4>Regions</h4>
          {regions.map(r => (
            <div 
              key={r.region_id} 
              className={`list-item ${selectedRegionId === r.region_id ? 'active' : ''}`}
              onClick={() => fetchAnalytics(r.region_id)}
            >
              <span>{r.region_name}</span>
            </div>
          ))}
        </div>

        <div style={{ marginTop: 'auto', paddingTop: '20px', borderTop: '2px solid var(--border-color)' }}>
          <div style={{ 
            marginBottom: '20px', 
            padding: '16px',
            background: 'var(--glass-bg)',
            borderRadius: '12px',
            border: '1px solid var(--border-subtle)',
            display: 'flex',
            alignItems: 'center',
            gap: '12px'
          }}>
            <div style={{
              width: '48px',
              height: '48px',
              borderRadius: '50%',
              background: 'linear-gradient(135deg, var(--accent-primary), var(--accent-hover))',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '20px',
              fontWeight: 'bold',
              color: 'white',
              boxShadow: '0 4px 12px rgba(83, 109, 254, 0.3)'
            }}>
              {userName ? userName.charAt(0).toUpperCase() : '?'}
            </div>
            <div style={{ flex: 1, overflow: 'hidden' }}>
              <div style={{ fontWeight: '600', fontSize: '14px', color: 'var(--text-primary)', marginBottom: '4px' }}>
                {userName || 'User'}
              </div>
              <div style={{ 
                fontSize: '11px', 
                color: 'var(--text-secondary)',
                textTransform: 'uppercase',
                fontWeight: '600',
                letterSpacing: '1px'
              }}>
                {userRole === 'admin' ? '👑 Admin' : '👤 Staff'}
              </div>
            </div>
          </div>
          <button 
            onClick={handleLogout} 
            style={{ marginBottom: '10px' }}
          >
            🚪 Logout
          </button>
          {userRole === 'admin' && (
            <button 
              onClick={handleResetDatabase} 
              className="danger"
              title="Admin only - This will delete all data"
            >
              ⚠️ Reset Database
            </button>
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="main-content">
        {/* Video Stage */}
        <div className="video-stage" style={{position: 'relative'}}>
          {currentVideoUrl ? (
            <video 
              ref={playbackRef}
              src={currentVideoUrl} 
              controls 
              autoPlay={isPlayingAll}
              style={{width: '100%', height: '100%', objectFit: 'contain'}}
              onError={(e) => {
                const video = e.target;
                const error = video.error;
                console.error('Video error:', error?.code, error?.message);
                // MediaError codes: 1=ABORTED, 2=NETWORK, 3=DECODE, 4=SRC_NOT_SUPPORTED
                if (error?.code === 4) {
                  alert('Video format not supported by browser. The video may need to be re-encoded with H.264 codec.');
                }
              }}
              onLoadedMetadata={(e) => {
                const video = e.target;
                // Calculate actual displayed video size (accounting for objectFit: contain)
                const containerWidth = video.clientWidth;
                const containerHeight = video.clientHeight;
                const videoAspect = video.videoWidth / video.videoHeight;
                const containerAspect = containerWidth / containerHeight;
                
                let displayWidth, displayHeight, offsetX, offsetY;
                
                if (videoAspect > containerAspect) {
                  // Video is wider - letterbox on top/bottom
                  displayWidth = containerWidth;
                  displayHeight = containerWidth / videoAspect;
                  offsetX = 0;
                  offsetY = (containerHeight - displayHeight) / 2;
                } else {
                  // Video is taller - letterbox on sides
                  displayHeight = containerHeight;
                  displayWidth = containerHeight * videoAspect;
                  offsetX = (containerWidth - displayWidth) / 2;
                  offsetY = 0;
                }
                
                setVideoScale({
                  x: displayWidth / video.videoWidth,
                  y: displayHeight / video.videoHeight,
                  offsetX: offsetX,
                  offsetY: offsetY
                });
              }}
              onEnded={() => {
                if (isPlayingAll) {
                  setCurrentShardIndex(prev => prev + 1);
                }
              }}
            />
          ) : (
            <div style={{color: '#666'}}>Select a camera with footage to view playback</div>
          )}
          
          {/* Region Overlay */}
          {selectedRegionId && regions.find(r => r.region_id === selectedRegionId) && (
            (() => {
              const r = regions.find(r => r.region_id === selectedRegionId);
              return (
                <>
                  <div 
                    style={{
                      position: 'absolute',
                      border: '2px solid rgba(255, 0, 0, 0.8)',
                      backgroundColor: 'rgba(255, 0, 0, 0.2)',
                      left: ((r.x1 * videoScale.x) + (videoScale.offsetX || 0)) + 'px',
                      top: ((r.y1 * videoScale.y) + (videoScale.offsetY || 0)) + 'px',
                      width: ((r.x2 - r.x1) * videoScale.x) + 'px',
                      height: ((r.y2 - r.y1) * videoScale.y) + 'px',
                      pointerEvents: 'none'
                    }}
                  >
                    <span style={{
                      position: 'absolute', 
                      top: '-20px', 
                      left: '0', 
                      background: 'red', 
                      color: 'white', 
                      padding: '2px 5px', 
                      fontSize: '12px'
                    }}>
                      {r.region_name}
                    </span>
                  </div>
                  {/* Heatmap Visualization */}
                  <HeatmapVisualization 
                    regionId={selectedRegionId} 
                    shardId={currentVideoUrl ? currentVideoUrl.split('/').pop().split('.')[0] : null}
                    videoScale={videoScale}
                  />
                </>
              );
            })()
          )}

          <div className="video-overlay">
            {isPlayingAll ? `Playing Sequence (${currentShardIndex + 1}/${cameraShards.length})` : 'Live / Manual'}
          </div>
        </div>

        {/* Controls */}
        <div className="control-panel">
          
          {/* Playback Controls */}
          <div className="panel-card">
            <h3>Playback Control</h3>
            <div style={{display: 'flex', gap: '10px', marginBottom: '10px'}}>
              <button onClick={() => {
                setIsPlayingAll(true);
                setCurrentShardIndex(0);
              }}>Play All Shards Seamlessly</button>
              <button className="secondary" onClick={() => setIsPlayingAll(false)}>Stop Sequence</button>
            </div>
            <small style={{color: '#888'}}>
              {cameraShards.length} shards available for this camera.
            </small>
          </div>

          {/* Analytics */}
          <div className="panel-card">
            <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px'}}>
              <h3>Region Analytics</h3>
              <div style={{display: 'flex', gap: '10px', alignItems: 'center'}}>
                <button 
                  onClick={handleExportCSV}
                  disabled={!selectedRegionId}
                  style={{
                    backgroundColor: '#2e7d32',
                    padding: '8px 15px',
                    fontSize: '0.85rem',
                    opacity: selectedRegionId ? 1 : 0.5,
                    cursor: selectedRegionId ? 'pointer' : 'not-allowed'
                  }}
                >
                  📥 Export CSV
                </button>
                <button 
                  onClick={() => setShowTrends(!showTrends)}
                  className="secondary"
                  style={{padding: '8px 15px', fontSize: '0.85rem'}}
                >
                  {showTrends ? '📊 Hide Trends' : '📈 Show Trends'}
                </button>
                <button 
                  onClick={() => setShowAIReports(!showAIReports)}
                  style={{
                    background: 'linear-gradient(135deg, #9c27b0, #673ab7)',
                    padding: '8px 15px', 
                    fontSize: '0.85rem'
                  }}
                >
                  {showAIReports ? '🤖 Hide AI Reports' : '🤖 AI Reports'}
                </button>
              </div>
            </div>
            
            {analyticsData ? (
              <div style={{display: 'flex', flexDirection: 'column', gap: '20px'}}>
                
                {/* Footfall & Time */}
                <div style={{maxHeight: '150px', overflowY: 'auto'}}>
                  <h4>Footfall & Dwell Time</h4>
                  <table className="analytics-table">
                    <thead>
                      <tr><th>Shard</th><th>Footfall</th><th>Avg Time</th></tr>
                    </thead>
                    <tbody>
                      {analyticsData.map((d, i) => (
                        <tr key={i}>
                          <td>{d.shardId.substring(0, 6)}...</td>
                          <td>{d.footfall}</td>
                          <td>{d.timeSpent ? d.timeSpent.toFixed(1) : 0}s</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Demographics */}
                <div>
                  <h4>Demographics (Gender)</h4>
                  <div style={{display: 'flex', gap: '10px'}}>
                    {demographicsData && demographicsData.length > 0 ? demographicsData.map((d, i) => (
                      <div key={i} style={{background: '#333', padding: '10px', borderRadius: '4px', flex: 1, textAlign: 'center'}}>
                        <div style={{fontSize: '1.2em', fontWeight: 'bold'}}>{d.count}</div>
                        <div style={{color: '#aaa'}}>{d.gender}</div>
                      </div>
                    )) : <div style={{color: '#666'}}>No demographics data</div>}
                  </div>
                </div>

                {/* Tracking Duration Stats */}
                <div>
                  <h4>Tracking Duration (Confusion Time)</h4>
                  <div style={{maxHeight: '100px', overflowY: 'auto'}}>
                    <table className="analytics-table">
                      <thead>
                        <tr><th>Shard</th><th>Avg Duration</th></tr>
                      </thead>
                      <tbody>
                        {trackingStats && trackingStats.map((d, i) => (
                          <tr key={i}>
                            <td>{d.video_shard.substring(0, 6)}...</td>
                            <td>{d.avg_confusion_time ? parseFloat(d.avg_confusion_time).toFixed(2) : 0}s</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

              </div>
            ) : (
              <p style={{color: '#666'}}>Select a region to view stats.</p>
            )}
          </div>

          {/* Historical Trends (conditional) */}
          {showTrends && selectedRegionId && (
            <TrendsPanel regionId={selectedRegionId} />
          )}

          {/* AI Reports Panel (conditional) */}
          {showAIReports && (
            <AIReportsPanel 
              regionId={selectedRegionId} 
              onClose={() => setShowAIReports(false)} 
            />
          )}

          {/* Annotation Tool */}
          <div className="panel-card" style={{gridColumn: '1 / -1'}}>
            <h3>Annotation Studio</h3>
            <div style={{display: 'flex', gap: '20px'}}>
              <div style={{flex: 1}}>
                <div className="tabs" style={{marginBottom: '10px'}}>
                  <button className={inputType==='upload'?'':'secondary'} onClick={() => setInputType('upload')} style={{width: 'auto', marginRight: '5px'}}>Upload</button>
                  <button className={inputType==='stream'?'':'secondary'} onClick={() => setInputType('stream')} style={{width: 'auto'}}>Stream</button>
                </div>
                {inputType === 'upload' ? (
                  <input type="file" accept="video/*" onChange={handleFileUpload} />
                ) : (
                  <input placeholder="RTSP URL" value={streamUrl} onChange={e => setStreamUrl(e.target.value)} />
                )}
                <input placeholder="New Region Name" value={regionName} onChange={e => setRegionName(e.target.value)} />
                
                <div style={{margin: '10px 0'}}>
                  <label style={{display: 'block', marginBottom: '5px', fontSize: '0.9em', color: '#aaa'}}>
                    Alert Threshold: {alertThreshold}s
                  </label>
                  <input 
                    type="range" 
                    min="1" 
                    max="60" 
                    value={alertThreshold} 
                    onChange={e => setAlertThreshold(parseInt(e.target.value))}
                    style={{width: '100%'}}
                  />
                </div>

                <div style={{display: 'flex', gap: '10px'}}>
                  <button onClick={handleSaveRegion}>Save Region</button>
                  {!isProcessing ? (
                    <button onClick={handleStartProcessing} style={{backgroundColor: '#2e7d32'}}>Start Processing</button>
                  ) : (
                    <button onClick={handleStopProcessing} style={{backgroundColor: '#d32f2f'}}>Stop Processing</button>
                  )}
                </div>
              </div>
              
              <div style={{flex: 2, position: 'relative', border: '1px solid #333', minHeight: '300px', backgroundColor: '#000'}}>
                {isProcessing && liveFrame ? (
                   <div style={{position: 'relative', width: '100%', height: '100%'}}>
                     <img 
                       ref={liveImgRef}
                       src={liveFrame} 
                       alt="Live Processing" 
                       style={{width: '100%', height: '100%', objectFit: 'contain'}} 
                       onLoad={(e) => {
                         const img = e.target;
                         // Only recalculate if dimensions have changed
                         if (!img.naturalWidth || !img.naturalHeight) return;
                         
                         const containerWidth = img.clientWidth;
                         const containerHeight = img.clientHeight;
                         const imgAspect = img.naturalWidth / img.naturalHeight;
                         const containerAspect = containerWidth / containerHeight;
                         
                         let displayWidth, displayHeight, offsetX, offsetY;
                         
                         if (imgAspect > containerAspect) {
                           displayWidth = containerWidth;
                           displayHeight = containerWidth / imgAspect;
                           offsetX = 0;
                           offsetY = (containerHeight - displayHeight) / 2;
                         } else {
                           displayHeight = containerHeight;
                           displayWidth = containerHeight * imgAspect;
                           offsetX = (containerWidth - displayWidth) / 2;
                           offsetY = 0;
                         }
                         
                         const newScaleX = displayWidth / img.naturalWidth;
                         const newScaleY = displayHeight / img.naturalHeight;
                         
                         // Only update if values have changed (prevent unnecessary re-renders)
                         setLiveScale(prev => {
                           if (Math.abs(prev.x - newScaleX) > 0.001 || 
                               Math.abs(prev.y - newScaleY) > 0.001 ||
                               Math.abs((prev.offsetX || 0) - offsetX) > 0.5 ||
                               Math.abs((prev.offsetY || 0) - offsetY) > 0.5) {
                             return {
                               x: newScaleX,
                               y: newScaleY,
                               offsetX: offsetX,
                               offsetY: offsetY
                             };
                           }
                           return prev;
                         });
                       }}
                     />
                     
                     {/* Live Region Overlay */}
                     {regions.filter(r => r.cam_id === parseInt(selectedCamId)).map(r => (
                        <div 
                          key={r.region_id}
                          style={{
                            position: 'absolute',
                            border: '2px solid rgba(0, 255, 0, 0.5)',
                            backgroundColor: 'rgba(0, 255, 0, 0.1)',
                            left: ((r.x1 * liveScale.x) + (liveScale.offsetX || 0)) + 'px',
                            top: ((r.y1 * liveScale.y) + (liveScale.offsetY || 0)) + 'px',
                            width: ((r.x2 - r.x1) * liveScale.x) + 'px',
                            height: ((r.y2 - r.y1) * liveScale.y) + 'px',
                            pointerEvents: 'none'
                          }}
                        >
                          <span style={{
                            position: 'absolute', 
                            top: '-20px', 
                            left: '0', 
                            background: 'rgba(0, 255, 0, 0.7)', 
                            color: 'white', 
                            padding: '2px 5px', 
                            fontSize: '10px'
                          }}>
                            {r.region_name}
                          </span>
                        </div>
                     ))}
                   </div>
                ) : (
                  videoSource && (
                    <video 
                      ref={videoRef}
                      src={videoSource} 
                      controls 
                      style={{ width: '100%', display: 'block' }}
                      onLoadedMetadata={() => {
                        if(canvasRef.current && videoRef.current) {
                          canvasRef.current.width = videoRef.current.clientWidth;
                          canvasRef.current.height = videoRef.current.clientHeight;
                        }
                      }}
                    />
                  )
                )}
                {!isProcessing && (
                  <canvas
                    ref={canvasRef}
                    style={{ position: 'absolute', top: 0, left: 0, pointerEvents: videoSource ? 'auto' : 'none' }}
                    onMouseDown={handleMouseDown}
                    onMouseMove={handleMouseMove}
                    onMouseUp={handleMouseUp}
                  />
                )}
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}

export default Dashboard;
