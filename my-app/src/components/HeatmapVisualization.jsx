import React from 'react';

const HeatmapVisualization = ({ regionId, shardId, videoScale, containerRef }) => {
  const [heatmapData, setHeatmapData] = React.useState(null);
  const [showHeatmap, setShowHeatmap] = React.useState(false);
  const [isLoading, setIsLoading] = React.useState(false);
  const [error, setError] = React.useState(null);
  const canvasRef = React.useRef(null);

  React.useEffect(() => {
    if (regionId && showHeatmap) {
      fetchHeatmap();
    }
  }, [regionId, shardId, showHeatmap]);

  // Redraw on resize
  React.useEffect(() => {
    if (heatmapData && showHeatmap) {
      drawHeatmap(heatmapData);
    }
  }, [videoScale]);

  const fetchHeatmap = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const url = shardId
        ? `http://localhost:8000/api/analytics/heatmap/${regionId}?shard_id=${shardId}`
        : `http://localhost:8000/api/analytics/heatmap/${regionId}`;
      
      const res = await fetch(url);
      if (!res.ok) throw new Error('Failed to fetch heatmap data');
      
      const data = await res.json();
      if (!data.data || !data.data.cells) {
        setError('No heatmap data available for this region');
        setHeatmapData(null);
        return;
      }
      setHeatmapData(data.data);
      drawHeatmap(data.data);
    } catch (err) {
      console.error('Error fetching heatmap:', err);
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const drawHeatmap = (data) => {
    if (!canvasRef.current || !data || !data.cells || data.cells.length === 0) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    
    // Set canvas size to match container
    const parent = canvas.parentElement;
    if (parent) {
      canvas.width = parent.clientWidth || 800;
      canvas.height = parent.clientHeight || 600;
    }
    
    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Find max density for normalization
    const maxDensity = Math.max(...data.cells.map(c => c.density), 1);

    const { x1, x2, y1, y2 } = data.region_bounds;
    const scaleX = videoScale?.x || 1;
    const scaleY = videoScale?.y || 1;
    const offsetX = videoScale?.offsetX || 0;
    const offsetY = videoScale?.offsetY || 0;
    
    const regionWidth = (x2 - x1) * scaleX;
    const regionHeight = (y2 - y1) * scaleY;
    const regionOffsetX = (x1 * scaleX) + offsetX;
    const regionOffsetY = (y1 * scaleY) + offsetY;
    
    const { width: gridWidth, height: gridHeight } = data.grid_size;
    const cellWidth = regionWidth / gridWidth;
    const cellHeight = regionHeight / gridHeight;

    // Draw heat map cells
    data.cells.forEach(cell => {
      const intensity = cell.density / maxDensity;
      const alpha = 0.3 + intensity * 0.5; // 30% to 80% opacity

      // Color gradient: blue (low) -> cyan -> green -> yellow -> red (high)
      let r, g, b;
      if (intensity < 0.25) {
        r = 0;
        g = Math.floor(255 * (intensity * 4));
        b = 255;
      } else if (intensity < 0.5) {
        r = 0;
        g = 255;
        b = Math.floor(255 * (1 - (intensity - 0.25) * 4));
      } else if (intensity < 0.75) {
        r = Math.floor(255 * ((intensity - 0.5) * 4));
        g = 255;
        b = 0;
      } else {
        r = 255;
        g = Math.floor(255 * (1 - (intensity - 0.75) * 4));
        b = 0;
      }

      ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${alpha})`;
      ctx.fillRect(
        regionOffsetX + cell.x * cellWidth,
        regionOffsetY + cell.y * cellHeight,
        cellWidth + 1,  // +1 to prevent gaps
        cellHeight + 1
      );
    });
    
    // Draw region outline
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.5)';
    ctx.lineWidth = 2;
    ctx.strokeRect(regionOffsetX, regionOffsetY, regionWidth, regionHeight);
  };

  if (!showHeatmap) {
    return (
      <button
        onClick={() => setShowHeatmap(true)}
        style={{
          position: 'absolute',
          top: '10px',
          right: '10px',
          zIndex: 100,
          padding: '8px 15px',
          backgroundColor: '#2e7d32',
          color: 'white',
          border: 'none',
          borderRadius: '5px',
          cursor: 'pointer',
        }}
      >
        🔥 Show Heatmap
      </button>
    );
  }

  return (
    <>
      <button
        onClick={() => setShowHeatmap(false)}
        style={{
          position: 'absolute',
          top: '10px',
          right: '10px',
          zIndex: 100,
          padding: '8px 15px',
          backgroundColor: '#d32f2f',
          color: 'white',
          border: 'none',
          borderRadius: '5px',
          cursor: 'pointer',
        }}
      >
        ✕ Hide Heatmap
      </button>
      
      {isLoading && (
        <div style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          background: 'rgba(0,0,0,0.8)',
          padding: '20px',
          borderRadius: '10px',
          color: 'white',
        }}>
          Loading heatmap...
        </div>
      )}
      
      {error && (
        <div style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          background: 'rgba(200,50,50,0.9)',
          padding: '20px',
          borderRadius: '10px',
          color: 'white',
        }}>
          {error}
        </div>
      )}
      
      <canvas
        ref={canvasRef}
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          pointerEvents: 'none',
          width: '100%',
          height: '100%',
        }}
      />
      {heatmapData && (
        <div
          style={{
            position: 'absolute',
            bottom: '10px',
            right: '10px',
            background: 'rgba(0, 0, 0, 0.8)',
            padding: '10px',
            borderRadius: '5px',
            fontSize: '12px',
          }}
        >
          <div style={{ fontWeight: 'bold', marginBottom: '5px' }}>Activity Heat Map</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <span>Low</span>
            <div
              style={{
                width: '100px',
                height: '15px',
                background: 'linear-gradient(to right, blue, green, yellow, red)',
              }}
            />
            <span>High</span>
          </div>
        </div>
      )}
    </>
  );
};

export default HeatmapVisualization;
