import React, { useState, useEffect } from 'react';
import './BulldogLoader.css';

const BulldogLoader = ({ startTime }) => {
  const [timeElapsed, setTimeElapsed] = useState(0);
  const [estimatedRemaining, setEstimatedRemaining] = useState('Calculating...');

  useEffect(() => {
    const interval = setInterval(() => {
      const elapsed = Math.floor((Date.now() - startTime) / 1000);
      setTimeElapsed(elapsed);

      // Estimate remaining time (5 min = 300 sec total)
      const totalEstimated = 300;
      const remaining = Math.max(0, totalEstimated - elapsed);
      
      if (remaining > 0) {
        const minutes = Math.floor(remaining / 60);
        const seconds = remaining % 60;
        setEstimatedRemaining(`About ${minutes}:${seconds.toString().padStart(2, '0')} remaining`);
      } else {
        setEstimatedRemaining('Almost done...');
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [startTime]);

  return (
    <div className="bulldog-loader-container">
      <div className="bulldog-animation">
        {/* Yale Bulldog SVG - simplified and animated */}
        <svg className="bulldog-svg" viewBox="0 0 200 120" xmlns="http://www.w3.org/2000/svg">
          {/* Body - tan/beige bulldog body */}
          <ellipse cx="100" cy="75" rx="48" ry="30" fill="#D4A574" className="bulldog-body"/>
          <ellipse cx="100" cy="75" rx="42" ry="25" fill="#C9955D" opacity="0.3"/>
          
          {/* Head - large, wide bulldog head */}
          <ellipse cx="100" cy="48" rx="30" ry="28" fill="#D4A574" className="bulldog-head"/>
          
          {/* Jowls - droopy bulldog cheeks */}
          <ellipse cx="80" cy="60" rx="14" ry="16" fill="#C9955D" opacity="0.7"/>
          <ellipse cx="120" cy="60" rx="14" ry="16" fill="#C9955D" opacity="0.7"/>
          
          {/* Ears - floppy bulldog ears */}
          <ellipse cx="75" cy="40" rx="12" ry="18" fill="#B8864E" className="bulldog-ear-left" transform="rotate(-30 75 40)"/>
          <ellipse cx="125" cy="40" rx="12" ry="18" fill="#B8864E" className="bulldog-ear-right" transform="rotate(30 125 40)"/>
          
          {/* Snout - wide, flat bulldog muzzle */}
          <ellipse cx="100" cy="58" rx="20" ry="14" fill="#E5C29F"/>
          <ellipse cx="100" cy="56" rx="17" ry="10" fill="#F0D5B8"/>
          
          {/* Nose - large, wide bulldog nose */}
          <ellipse cx="100" cy="60" rx="7" ry="5" fill="#3D2817"/>
          <ellipse cx="97" cy="59" rx="2" ry="2" fill="#000"/>
          <ellipse cx="103" cy="59" rx="2" ry="2" fill="#000"/>
          <line x1="100" y1="60" x2="100" y2="66" stroke="#3D2817" strokeWidth="2"/>
          
          {/* Mouth - slight underbite */}
          <path d="M 90 66 Q 100 68 110 66" stroke="#3D2817" strokeWidth="1.5" fill="none"/>
          
          {/* Eyes - small, expressive bulldog eyes */}
          <ellipse cx="86" cy="46" rx="5" ry="6" fill="#fff"/>
          <circle cx="86" cy="47" r="3" fill="#3D2817"/>
          <circle cx="85" cy="46" r="1.5" fill="#fff"/>
          <ellipse cx="114" cy="46" rx="5" ry="6" fill="#fff"/>
          <circle cx="114" cy="47" r="3" fill="#3D2817"/>
          <circle cx="113" cy="46" r="1.5" fill="#fff"/>
          
          {/* Wrinkles - signature bulldog wrinkles */}
          <path d="M 80 38 Q 100 36 120 38" stroke="#B8864E" strokeWidth="2.5" fill="none" opacity="0.6"/>
          <path d="M 83 42 Q 100 40 117 42" stroke="#B8864E" strokeWidth="2" fill="none" opacity="0.5"/>
          <path d="M 75 50 Q 80 52 85 50" stroke="#B8864E" strokeWidth="2" fill="none" opacity="0.4"/>
          <path d="M 115 50 Q 120 52 125 50" stroke="#B8864E" strokeWidth="2" fill="none" opacity="0.4"/>
          
          {/* Legs - short, muscular bulldog legs */}
          <rect x="72" y="95" width="12" height="16" rx="6" fill="#D4A574" className="bulldog-leg leg-1"/>
          <rect x="86" y="95" width="12" height="16" rx="6" fill="#D4A574" className="bulldog-leg leg-2"/>
          <rect x="102" y="95" width="12" height="16" rx="6" fill="#D4A574" className="bulldog-leg leg-3"/>
          <rect x="116" y="95" width="12" height="16" rx="6" fill="#D4A574" className="bulldog-leg leg-4"/>
          
          {/* Paws - white paws */}
          <ellipse cx="78" cy="109" rx="7" ry="4" fill="#F5F5F5"/>
          <ellipse cx="92" cy="109" rx="7" ry="4" fill="#F5F5F5"/>
          <ellipse cx="108" cy="109" rx="7" ry="4" fill="#F5F5F5"/>
          <ellipse cx="122" cy="109" rx="7" ry="4" fill="#F5F5F5"/>
          
          {/* Tail - short, stumpy bulldog tail */}
          <ellipse cx="145" cy="77" rx="8" ry="6" fill="#D4A574" className="bulldog-tail" transform="rotate(45 145 77)"/>
          
          {/* White chest patch */}
          <ellipse cx="100" cy="85" rx="18" ry="12" fill="#F5F5F5" opacity="0.9"/>
          
          {/* Collar with Y - Yale blue */}
          <rect x="85" y="70" width="30" height="8" rx="2" fill="#003087"/>
          <text x="100" y="77" fontFamily="Arial, sans-serif" fontSize="8" fontWeight="bold" fill="#fff" textAnchor="middle">Y</text>
        </svg>
      </div>

      <div className="loading-text">
        <h3>🐕 Analyzing your syllabus...</h3>
        <p className="loading-message">Our AI bulldog is fetching your deadlines and assignments!</p>
        <p className="time-estimate">{estimatedRemaining}</p>
        <div className="loading-dots">
          <span></span>
          <span></span>
          <span></span>
        </div>
      </div>
    </div>
  );
};

export default BulldogLoader;
