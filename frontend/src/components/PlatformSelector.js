import React from 'react';
import { Button } from './ui/button';
import { Instagram } from 'lucide-react';

const FacebookIcon = ({ className }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor">
    <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
  </svg>
);

const PlatformSelector = ({ selectedPlatform, onPlatformChange }) => {
  const platforms = [
    { id: 'all', label: 'All Platforms', icon: null },
    { id: 'instagram', label: 'Instagram', icon: Instagram },
    { id: 'facebook', label: 'Facebook', icon: FacebookIcon }
  ];

  return (
    <div className="flex space-x-2 bg-[#1a1a2e] border border-gray-800 rounded-lg p-1" data-testid="platform-selector">
      {platforms.map((platform) => {
        const Icon = platform.icon;
        const isSelected = selectedPlatform === platform.id;
        
        return (
          <Button
            key={platform.id}
            onClick={() => onPlatformChange(platform.id)}
            variant={isSelected ? "default" : "ghost"}
            size="sm"
            className={`flex items-center space-x-2 ${
              isSelected
                ? 'bg-gradient-to-r from-purple-600 to-pink-600 text-white hover:from-purple-700 hover:to-pink-700'
                : 'text-gray-400 hover:text-white hover:bg-[#0f0f1a]'
            }`}
            data-testid={`platform-${platform.id}`}
          >
            {Icon && <Icon className="w-4 h-4" />}
            <span className="text-sm font-medium">{platform.label}</span>
          </Button>
        );
      })}
    </div>
  );
};

export default PlatformSelector;
