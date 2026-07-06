const {
  useState,
  useEffect,
  useCallback
} = React;
const {
  createRoot
} = ReactDOM;
const EFFECT_MAP = {
  'Animated Rainbow Name': 'rainbow-name',
  'Gold Username': 'gold-name',
  'Flame Profile Border': 'flame-border',
  'Electric Profile Border': 'electric-border',
  'Shooting Star Effect': 'shooting-stars',
  'Blood Moon Effect': 'blood-moon',
  'Void Effect': 'void',
  'Holographic Name': 'holo',
  'Matrix Rain': 'matrix',
  'Angel Effect': 'angel',
  'Demon Effect': 'demon',
  'Galaxy Effect': 'galaxy',
  'Neon Sign': 'neon',
  'Cyberpunk Effect': 'cyber',
  'Sakura Effect': 'sakura',
  'Lava Effect': 'lava',
  'Shadow Effect': 'shadow',
  'Thunder Effect': 'thunder',
  'Saturn Ring': 'ring',
  'Cursed Effect': 'cursed',
  'Crypto Ticker': 'crypto',
  'Pixel Name': 'pixel',
  'Dragon Effect': 'dragon',
  'Sunrise Effect': 'sunrise',
  'Overloaded Effect': 'overload',
  'Bounty Hunter': 'bounty',
  'Frostbite Effect': 'frost',
  'Nepal Name': 'nepal',
  'Toxic Name': 'toxic',
  'Ice Border': 'ice',
  'Glitch Name': 'glitch',
  'Stardust Burst': 'stardust',
  'Ember Sparks': 'ember-sparks',
  'Snowfall': 'snowfall',
  'Energy Arc': 'energy-arc',
  'Neon Rain': 'neon-rain',
  'Spirit Orbs': 'spirit-orbs',
  'Sakura Storm': 'sakura-storm',
  'Ocean Depths': 'ocean-depths',
  'Sunset Horizon': 'sunset-horizon',
  'Cosmic Nebula': 'cosmic-nebula',
  'Neon Grid': 'neon-grid',
  'Starry Sky': 'starry-sky',
  'Lava Flow': 'lava-flow',
  'Crystal Aura': 'crystal-aura',
  'Frostwind': 'frostwind',
  'Thunder Storm': 'thunder-storm',
  'Fire Spirit': 'fire-spirit',
  'Mystic Mist': 'mystic-mist'
};
const NAME_EFFECTS = new Set(['rainbow-name', 'gold-name', 'matrix', 'neon', 'cyber', 'pixel', 'crypto', 'bounty', 'nepal', 'toxic', 'glitch', 'cursed', 'shadow', 'holo', 'sakura', 'galaxy', 'ring']);
const BORDER_EFFECTS = new Set(['flame-border', 'electric-border', 'ice', 'frost', 'blood-moon', 'void', 'lava', 'dragon', 'sunrise', 'overload', 'thunder']);
const AVATAR_EFFECTS = new Set(['shooting-stars', 'angel', 'demon', 'sakura-storm', 'ocean-depths', 'sunset-horizon', 'cosmic-nebula', 'neon-grid', 'starry-sky', 'lava-flow', 'crystal-aura', 'frostwind', 'thunder-storm', 'fire-spirit', 'mystic-mist', 'stardust', 'ember-sparks', 'snowfall', 'energy-arc', 'neon-rain', 'spirit-orbs']);
function getSlot(item) {
  if (item.category === 'lootbox') return 'crate';
  if (item.category === 'boosts') return 'boost';
  if (!item.name) return 'other';
  if (item.name.startsWith('Title:') || item.name === 'Custom Title' || item.name === 'Global Shoutout 24hr' || item.name === 'Leaderboard Pin 24hr') return 'title';
  const k = EFFECT_MAP[item.name];
  if (k && NAME_EFFECTS.has(k)) return 'name';
  if (k && BORDER_EFFECTS.has(k)) return 'border';
  if (k && AVATAR_EFFECTS.has(k)) return 'avatar';
  return 'other';
}
function getCSRF() {
  const m = document.cookie.match(/csrftoken=([^;]+)/);
  return m ? m[1] : '';
}
const SLOT_LABELS = {
  title: 'Title',
  name: 'Name Effect',
  border: 'Border',
  avatar: 'Avatar FX',
  boost: 'Boost',
  crate: 'Crate',
  other: 'Other'
};
const SLOT_ICONS = {
  title: '👑',
  name: '✨',
  border: '🔥',
  avatar: '💫',
  boost: '⚡',
  crate: '📦',
  other: '🎁'
};
const SLOT_CSS = {
  title: 'slot-title',
  name: 'slot-name',
  border: 'slot-border',
  avatar: 'slot-avatar',
  boost: 'slot-boost',
  crate: '',
  other: ''
};
const EFFECT_LABELS = {
  'rainbow-name': 'Rainbow',
  'gold-name': 'Gold',
  'glitch': 'Glitch',
  'matrix': 'Matrix',
  'neon': 'Neon',
  'cyber': 'Cyberpunk',
  'pixel': 'Pixel',
  'crypto': 'Crypto',
  'bounty': 'Bounty',
  'nepal': 'Nepal #1',
  'toxic': 'Toxic',
  'cursed': 'Cursed',
  'shadow': 'Shadow',
  'holo': 'Holographic',
  'sakura': 'Sakura',
  'galaxy': 'Galaxy',
  'ring': 'Saturn Ring',
  'flame-border': 'Flame',
  'electric-border': 'Electric',
  'ice': 'Ice',
  'frost': 'Frostbite',
  'blood-moon': 'Blood Moon',
  'void': 'Void',
  'lava': 'Lava',
  'dragon': 'Dragon',
  'sunrise': 'Sunrise',
  'overload': 'Overloaded',
  'thunder': 'Thunder',
  'shooting-stars': 'Shooting Stars',
  'angel': 'Angel',
  'demon': 'Demon',
  'sakura-storm': 'Sakura Storm',
  'ocean-depths': 'Ocean Depths',
  'sunset-horizon': 'Sunset Horizon',
  'cosmic-nebula': 'Cosmic Nebula',
  'neon-grid': 'Neon Grid',
  'starry-sky': 'Starry Sky',
  'lava-flow': 'Lava Flow',
  'crystal-aura': 'Crystal Aura',
  'frostwind': 'Frostwind',
  'thunder-storm': 'Thunder Storm',
  'fire-spirit': 'Fire Spirit',
  'mystic-mist': 'Mystic Mist',
  'stardust': 'Stardust Burst',
  'ember-sparks': 'Ember Sparks',
  'snowfall': 'Snowfall',
  'energy-arc': 'Energy Arc',
  'neon-rain': 'Neon Rain',
  'spirit-orbs': 'Spirit Orbs'
};
const EFFECT_EMOJIS = {
  'rainbow-name': '🌈',
  'gold-name': '✨',
  'glitch': '💻',
  'matrix': '🟢',
  'neon': '💡',
  'cyber': '🤖',
  'pixel': '🕹️',
  'crypto': '📈',
  'bounty': '🎯',
  'nepal': '🇳🇵',
  'toxic': '☠️',
  'cursed': '👁️',
  'shadow': '🌑',
  'holo': '💿',
  'sakura': '🌸',
  'galaxy': '🌌',
  'ring': '🪐',
  'flame-border': '🔥',
  'electric-border': '⚡',
  'ice': '❄️',
  'frost': '🧊',
  'blood-moon': '🌑',
  'void': '🕳️',
  'lava': '🌋',
  'dragon': '🐉',
  'sunrise': '🌅',
  'overload': '💥',
  'thunder': '⛈️',
  'shooting-stars': '🌟',
  'angel': '😇',
  'demon': '😈',
  'sakura-storm': '🌸',
  'ocean-depths': '🌊',
  'sunset-horizon': '🌅',
  'cosmic-nebula': '🌌',
  'neon-grid': '🏙️',
  'starry-sky': '✨',
  'lava-flow': '🌋',
  'crystal-aura': '💎',
  'frostwind': '❄️',
  'thunder-storm': '⛈️',
  'fire-spirit': '🔥',
  'mystic-mist': '🌫️',
  'stardust': '✨',
  'ember-sparks': '🔥',
  'snowfall': '❄️',
  'energy-arc': '⚡',
  'neon-rain': '🌧️',
  'spirit-orbs': '🔮'
};
function ProfilePreview({
  user,
  effects,
  onAvatarClick,
  inventoryItems,
  onToggle
}) {
  const [selBadge, setSelBadge] = React.useState(null);
  const allEffects = [effects.flex_effect ? 'flex-effect-' + effects.flex_effect : '', effects.name_effect ? 'flex-effect-' + effects.name_effect : '', effects.avatar_border ? 'flex-effect-' + effects.avatar_border : '', effects.bg_effect ? 'flex-effect-' + effects.bg_effect : ''].filter(Boolean).join(' ');
  const badges = [];
  if (effects.title) badges.push({
    cls: 'title-badge rainbow-badge',
    icon: '👑',
    label: effects.title,
    effectType: 'title',
    effectKey: effects.title,
    slot: 'Title'
  });
  if (effects.name_effect) badges.push({
    cls: 'name-badge',
    icon: EFFECT_EMOJIS[effects.name_effect] || '✨',
    label: EFFECT_LABELS[effects.name_effect] || effects.name_effect,
    effectType: 'name',
    effectKey: effects.name_effect,
    slot: 'Name FX'
  });
  if (effects.avatar_border) badges.push({
    cls: 'border-badge',
    icon: EFFECT_EMOJIS[effects.avatar_border] || '🔥',
    label: EFFECT_LABELS[effects.avatar_border] || effects.avatar_border,
    effectType: 'border',
    effectKey: effects.avatar_border,
    slot: 'Border FX'
  });
  if (effects.bg_effect) badges.push({
    cls: 'avatar-badge',
    icon: EFFECT_EMOJIS[effects.bg_effect] || '💫',
    label: EFFECT_LABELS[effects.bg_effect] || effects.bg_effect,
    effectType: 'avatar',
    effectKey: effects.bg_effect,
    slot: 'Avatar FX'
  });
  const activeCount = [effects.name_effect, effects.avatar_border, effects.bg_effect, effects.title].filter(Boolean).length;
  const powerLevels = ['', 'C', 'B', 'A', 'S'];
  const power = powerLevels[activeCount] || 'S';
  const powerColors = {
    'C': '#6b7280',
    'B': '#3b82f6',
    'A': '#a78bfa',
    'S': '#f59e0b'
  };
  const avatarUrl = user.has_avatar ? '/api/shop/avatar/?t=' + Date.now() : null;
  const handleBadgeClick = badge => {
    setSelBadge(badge);
  };
  const handleDeactivate = () => {
    if (!selBadge || !onToggle || !inventoryItems) return;
    if (selBadge.effectType === 'title') {
      const inv = inventoryItems.find(it => it.name.startsWith('Title:') && it.is_active);
      if (inv) onToggle(inv.id, inv.category, inv.name);
    } else {
      const revMap = Object.fromEntries(Object.entries(EFFECT_MAP).map(([k, v]) => [v, k]));
      const effectName = revMap[selBadge.effectKey];
      if (effectName) {
        const inv = inventoryItems.find(it => it.name === effectName);
        if (inv) onToggle(inv.id, inv.category, inv.name);
      }
    }
    setSelBadge(null);
  };
  const slotColors = {
    'Title': {
      bg: 'rgba(245,158,11,0.15)',
      color: '#f59e0b',
      border: 'rgba(245,158,11,0.3)'
    },
    'Name FX': {
      bg: 'rgba(167,139,250,0.15)',
      color: '#a78bfa',
      border: 'rgba(167,139,250,0.3)'
    },
    'Border FX': {
      bg: 'rgba(239,68,68,0.15)',
      color: '#ef4444',
      border: 'rgba(239,68,68,0.3)'
    },
    'Avatar FX': {
      bg: 'rgba(75,204,241,0.15)',
      color: '#4bccf1',
      border: 'rgba(75,204,241,0.3)'
    }
  };
  return /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    className: `preview-card ${allEffects}`
  }, /*#__PURE__*/React.createElement("div", {
    className: "preview-avatar",
    style: avatarUrl ? {
      backgroundImage: `url(${avatarUrl})`
    } : {
      onClick: onAvatarClick
    },
    onClick: onAvatarClick,
    title: "Click to change avatar"
  }, !avatarUrl && (user.display_name ? user.display_name[0].toUpperCase() : '?'), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      bottom: 2,
      right: 2,
      width: 22,
      height: 22,
      borderRadius: '50%',
      background: 'rgba(0,0,0,0.6)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontSize: 11,
      border: '2px solid rgba(74,158,196,0.5)'
    }
  }, "📷")), /*#__PURE__*/React.createElement("div", {
    className: "preview-info"
  }, /*#__PURE__*/React.createElement("div", {
    className: "preview-name"
  }, user.display_name), effects.title && /*#__PURE__*/React.createElement("div", {
    className: "preview-title",
    "data-text": effects.title
  }, effects.title)), /*#__PURE__*/React.createElement("div", {
    className: "preview-right"
  }, /*#__PURE__*/React.createElement("div", {
    className: "preview-power",
    style: {
      color: powerColors[power]
    }
  }, power), /*#__PURE__*/React.createElement("div", {
    className: "preview-power-label"
  }, "RANK"), /*#__PURE__*/React.createElement("div", {
    className: "preview-effects-count"
  }, activeCount, " FX"))), badges.length > 0 && /*#__PURE__*/React.createElement("div", {
    className: "preview-badges-row"
  }, badges.map((b, i) => /*#__PURE__*/React.createElement("span", {
    key: i,
    className: `preview-badge ${b.cls}`,
    style: {
      animationDelay: `${i * 100}ms`,
      cursor: 'pointer'
    },
    title: "Click for details",
    onClick: () => handleBadgeClick(b)
  }, b.icon, " ", b.label))), selBadge && /*#__PURE__*/React.createElement("div", {
    className: "fx-popup-overlay",
    onClick: e => {
      if (e.target === e.currentTarget) setSelBadge(null);
    }
  }, /*#__PURE__*/React.createElement("div", {
    className: "fx-popup"
  }, /*#__PURE__*/React.createElement("button", {
    className: "fx-popup-close",
    onClick: () => setSelBadge(null)
  }, "✕"), /*#__PURE__*/React.createElement("div", {
    className: "fx-popup-icon"
  }, selBadge.icon), /*#__PURE__*/React.createElement("div", {
    className: "fx-popup-name"
  }, selBadge.label), /*#__PURE__*/React.createElement("div", {
    className: "fx-popup-type"
  }, /*#__PURE__*/React.createElement("span", {
    className: "fx-popup-type-badge",
    style: {
      background: slotColors[selBadge.slot]?.bg,
      color: slotColors[selBadge.slot]?.color,
      border: `1px solid ${slotColors[selBadge.slot]?.border}`
    }
  }, selBadge.slot)), /*#__PURE__*/React.createElement("div", {
    className: `fx-popup-preview flex-effect-${selBadge.effectKey}`
  }, /*#__PURE__*/React.createElement("div", {
    className: "fx-popup-preview-name"
  }, user.display_name || 'USERNAME')), /*#__PURE__*/React.createElement("div", {
    className: "fx-popup-actions"
  }, /*#__PURE__*/React.createElement("button", {
    className: "fx-popup-btn deactivate",
    onClick: handleDeactivate
  }, "⏸ DEACTIVATE"), /*#__PURE__*/React.createElement("button", {
    className: "fx-popup-btn close",
    onClick: () => setSelBadge(null)
  }, "CLOSE")))));
}
function AvatarUploadModal({
  onClose,
  onSave
}) {
  const [preview, setPreview] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const handleFile = file => {
    if (!file || !file.type.startsWith('image/')) return;
    const reader = new FileReader();
    reader.onload = e => setPreview(e.target.result);
    reader.readAsDataURL(file);
  };
  const handleDrop = e => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    handleFile(file);
  };
  const handleUpload = async () => {
    if (!preview) return;
    setUploading(true);
    try {
      const res = await fetch('/api/shop/avatar-upload/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCSRF()
        },
        body: JSON.stringify({
          image: preview
        })
      });
      const data = await res.json();
      if (res.ok) {
        onSave(data.image);
        onClose();
      } else showAlert(data.error || 'Upload failed');
    } catch (e) {
      showAlert('Network error');
    }
    setUploading(false);
  };
  return /*#__PURE__*/React.createElement("div", {
    className: "modal-overlay",
    onClick: onClose
  }, /*#__PURE__*/React.createElement("div", {
    className: "modal-box",
    onClick: e => e.stopPropagation()
  }, /*#__PURE__*/React.createElement("div", {
    className: "modal-title"
  }, /*#__PURE__*/React.createElement("span", null, "📷"), " Change Avatar", /*#__PURE__*/React.createElement("button", {
    className: "modal-close",
    onClick: onClose
  }, "✕")), /*#__PURE__*/React.createElement("div", {
    className: `ai-upload-zone ${dragging ? 'dragging' : ''}`,
    onDragOver: e => {
      e.preventDefault();
      setDragging(true);
    },
    onDragLeave: () => setDragging(false),
    onDrop: handleDrop,
    onClick: () => document.getElementById('avatar-file-input').click()
  }, preview ? /*#__PURE__*/React.createElement("img", {
    src: preview,
    style: {
      maxWidth: '100%',
      maxHeight: 200,
      borderRadius: 10
    }
  }) : /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: '2.5rem',
      marginBottom: 8
    }
  }, "📁"), /*#__PURE__*/React.createElement("p", {
    style: {
      color: '#6b7280',
      fontSize: 13
    }
  }, "Drop image here or ", /*#__PURE__*/React.createElement("span", {
    style: {
      color: '#4a9ec4',
      fontWeight: 700
    }
  }, "browse")), /*#__PURE__*/React.createElement("p", {
    style: {
      color: '#4b5563',
      fontSize: 11,
      marginTop: 4
    }
  }, "PNG, JPG up to 5MB")), /*#__PURE__*/React.createElement("input", {
    id: "avatar-file-input",
    type: "file",
    accept: "image/*",
    style: {
      display: 'none'
    },
    onChange: e => handleFile(e.target.files[0])
  })), preview && /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 8,
      marginTop: 12
    }
  }, /*#__PURE__*/React.createElement("button", {
    style: {
      flex: 1,
      padding: 10,
      borderRadius: 8,
      border: '1px solid rgba(0,0,0,0.1)',
      background: 'transparent',
      color: '#6b7280',
      cursor: 'pointer',
      fontWeight: 700,
      fontSize: 12
    },
    onClick: () => setPreview(null)
  }, "Cancel"), /*#__PURE__*/React.createElement("button", {
    style: {
      flex: 1,
      padding: 10,
      borderRadius: 8,
      border: 'none',
      background: 'linear-gradient(135deg,#0d3b66,#4a9ec4)',
      color: '#fff',
      cursor: 'pointer',
      fontWeight: 700,
      fontSize: 12
    },
    onClick: handleUpload,
    disabled: uploading
  }, uploading ? '⏳ Uploading...' : '✅ Save Avatar'))));
}
function AIStudioModal({
  onClose,
  onSave,
  coins
}) {
  const [mode, setMode] = useState('upload');
  const [preview, setPreview] = useState(null);
  const [textPrompt, setTextPrompt] = useState('');
  const [style, setStyle] = useState('anime');
  const [prompt, setPrompt] = useState('');
  const [animate, setAnimate] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [result, setResult] = useState(null);
  const [resultAnimated, setResultAnimated] = useState(false);
  const [aiMeta, setAiMeta] = useState(null);
  const [dragging, setDragging] = useState(false);
  const styles = [{
    id: 'anime',
    icon: '🎌',
    label: 'Anime'
  }, {
    id: 'neon',
    icon: '💡',
    label: 'Neon'
  }, {
    id: 'vintage',
    icon: '📜',
    label: 'Vintage'
  }, {
    id: 'glitch',
    icon: '💻',
    label: 'Glitch'
  }, {
    id: 'oil',
    icon: '🎨',
    label: 'Oil Paint'
  }, {
    id: 'pop-art',
    icon: '🖼️',
    label: 'Pop Art'
  }, {
    id: 'cyberpunk',
    icon: '🤖',
    label: 'Cyberpunk'
  }, {
    id: 'watercolor',
    icon: '💧',
    label: 'Watercolor'
  }];
  const cost = 500 + (animate ? 300 : 0);
  const canAfford = coins >= cost;
  const handleFile = file => {
    if (!file || !file.type.startsWith('image/')) return;
    const reader = new FileReader();
    reader.onload = e => {
      setPreview(e.target.result);
      setResult(null);
    };
    reader.readAsDataURL(file);
  };
  const handleDrop = e => {
    e.preventDefault();
    setDragging(false);
    handleFile(e.dataTransfer.files[0]);
  };
  const handleGenerate = async () => {
    if (mode === 'upload' && !preview) return;
    if (mode === 'text' && !textPrompt.trim()) return;
    setProcessing(true);
    try {
      const body = mode === 'upload' ? {
        image: preview,
        style,
        prompt,
        animate
      } : {
        text_only: true,
        style,
        prompt: textPrompt + ' ' + prompt,
        animate
      };
      const res = await fetch('/api/shop/ai-profile/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCSRF()
        },
        body: JSON.stringify(body)
      });
      const data = await res.json();
      if (res.ok) {
        setResult(data.image);
        setResultAnimated(data.animated);
        setAiMeta({
          caption: data.ai_caption,
          params: data.ai_params,
          style: data.style,
          animated: data.animated
        });
        setPreview(null);
      } else showAlert(data.error || 'Gemini generation failed');
    } catch (e) {
      showAlert('Network error');
    }
    setProcessing(false);
  };
  const handleApply = () => {
    if (result) onSave(result);
    onClose();
  };
  return /*#__PURE__*/React.createElement("div", {
    className: "modal-overlay",
    onClick: onClose
  }, /*#__PURE__*/React.createElement("div", {
    className: "modal-box",
    onClick: e => e.stopPropagation(),
    style: {
      maxWidth: 480
    }
  }, /*#__PURE__*/React.createElement("div", {
    className: "modal-title"
  }, /*#__PURE__*/React.createElement("span", null, "🤖"), " AI Profile Studio", /*#__PURE__*/React.createElement("button", {
    className: "modal-close",
    onClick: onClose
  }, "✕")), !result ? /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 4,
      marginBottom: 12,
      background: '#f3f4f6',
      borderRadius: 8,
      padding: 3
    }
  }, /*#__PURE__*/React.createElement("button", {
    onClick: () => setMode('upload'),
    style: {
      flex: 1,
      padding: '6px 0',
      borderRadius: 6,
      border: 'none',
      cursor: 'pointer',
      fontWeight: 700,
      fontSize: 12,
      background: mode === 'upload' ? '#fff' : '#f3f4f6',
      color: mode === 'upload' ? '#0d3b66' : '#6b7280',
      boxShadow: mode === 'upload' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none'
    }
  }, "📷 Upload Photo"), /*#__PURE__*/React.createElement("button", {
    onClick: () => setMode('text'),
    style: {
      flex: 1,
      padding: '6px 0',
      borderRadius: 6,
      border: 'none',
      cursor: 'pointer',
      fontWeight: 700,
      fontSize: 12,
      background: mode === 'text' ? '#fff' : '#f3f4f6',
      color: mode === 'text' ? '#0d3b66' : '#6b7280',
      boxShadow: mode === 'text' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none'
    }
  }, "✍️ Describe")), mode === 'upload' ? /*#__PURE__*/React.createElement("div", {
    className: `ai-upload-zone ${dragging ? 'dragging' : ''}`,
    onDragOver: e => {
      e.preventDefault();
      setDragging(true);
    },
    onDragLeave: () => setDragging(false),
    onDrop: handleDrop,
    onClick: () => document.getElementById('ai-file-input').click()
  }, preview ? /*#__PURE__*/React.createElement("img", {
    src: preview,
    style: {
      maxWidth: '100%',
      maxHeight: 180,
      borderRadius: 10
    }
  }) : /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: '2.5rem',
      marginBottom: 8
    }
  }, "📁"), /*#__PURE__*/React.createElement("p", {
    style: {
      color: '#6b7280',
      fontSize: 13
    }
  }, "Drop photo or ", /*#__PURE__*/React.createElement("span", {
    style: {
      color: '#4a9ec4',
      fontWeight: 700
    }
  }, "browse"))), /*#__PURE__*/React.createElement("input", {
    id: "ai-file-input",
    type: "file",
    accept: "image/*",
    style: {
      display: 'none'
    },
    onChange: e => handleFile(e.target.files[0])
  })) : /*#__PURE__*/React.createElement("div", {
    style: {
      background: '#f9fafb',
      border: '2px dashed rgba(74,158,196,0.25)',
      borderRadius: 12,
      padding: 16,
      marginBottom: 12
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 12,
      fontWeight: 700,
      color: '#6b7280',
      marginBottom: 6
    }
  }, "Describe your avatar"), /*#__PURE__*/React.createElement("textarea", {
    className: "ai-prompt-input",
    placeholder: "e.g. a cool cyberpunk anime character with blue hair and glowing red eyes, dark moody background...",
    value: textPrompt,
    onChange: e => setTextPrompt(e.target.value),
    rows: 4
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      margin: '12px 0 8px',
      fontSize: 12,
      fontWeight: 700,
      color: '#6b7280'
    }
  }, "AI STYLE"), /*#__PURE__*/React.createElement("div", {
    className: "ai-style-grid"
  }, styles.map(s => /*#__PURE__*/React.createElement("button", {
    key: s.id,
    className: `ai-style-btn ${style === s.id ? 'selected' : ''}`,
    onClick: () => setStyle(s.id)
  }, /*#__PURE__*/React.createElement("span", {
    className: "style-icon"
  }, s.icon), s.label))), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 12,
      fontWeight: 700,
      color: '#6b7280',
      margin: '8px 0 4px'
    }
  }, "PROMPT (optional)"), /*#__PURE__*/React.createElement("textarea", {
    className: "ai-prompt-input",
    placeholder: "e.g. make it more colorful, add glow...",
    value: prompt,
    onChange: e => setPrompt(e.target.value)
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 8,
      margin: '10px 0'
    }
  }, /*#__PURE__*/React.createElement("label", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 6,
      cursor: 'pointer',
      fontSize: 12,
      color: '#6b7280'
    }
  }, /*#__PURE__*/React.createElement("input", {
    type: "checkbox",
    checked: animate,
    onChange: e => setAnimate(e.target.checked),
    style: {
      accentColor: '#4a9ec4',
      width: 16,
      height: 16
    }
  }), "✨ Animate (+Rs 300)")), /*#__PURE__*/React.createElement("div", {
    className: "ai-cost-tag",
    style: {
      opacity: canAfford ? 1 : 0.5
    }
  }, "Rs ", cost.toLocaleString(), " ", canAfford ? '' : '(not enough!)'), /*#__PURE__*/React.createElement("button", {
    className: "ai-pay-btn",
    disabled: mode === 'upload' && !preview || mode === 'text' && !textPrompt.trim() || !canAfford || processing,
    onClick: handleGenerate
  }, processing ? /*#__PURE__*/React.createElement(React.Fragment, null, "⏳ Gemini is generating...") : `🤖 Generate (Rs ${cost})`)) : /*#__PURE__*/React.createElement("div", {
    className: "ai-preview"
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 13,
      fontWeight: 700,
      color: '#22c55e',
      marginBottom: 8
    }
  }, "✅ Gemini Generated!"), aiMeta && /*#__PURE__*/React.createElement("div", {
    style: {
      background: '#f4f8fb',
      border: '1px solid rgba(74,158,196,0.15)',
      borderRadius: 8,
      padding: '8px 12px',
      marginBottom: 10,
      fontSize: 11,
      color: '#4a9ec4'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontWeight: 700,
      marginBottom: 4
    }
  }, "🤖 Gemini ", aiMeta.style?.charAt(0).toUpperCase() + aiMeta.style?.slice(1)), /*#__PURE__*/React.createElement("div", {
    style: {
      color: '#6b7280',
      fontStyle: 'italic'
    }
  }, "\"", aiMeta.caption, "\""), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'grid',
      gridTemplateColumns: '1fr 1fr',
      gap: '2px 12px',
      marginTop: 6,
      color: '#6b7280'
    }
  }, Object.entries(aiMeta.params || {}).map(([k, v]) => /*#__PURE__*/React.createElement("span", {
    key: k
  }, k, ": ", String(v)))), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 4,
      color: '#6b7280'
    }
  }, "Style: ", aiMeta.style, " ", aiMeta.animated ? '| Animated GIF' : '')), /*#__PURE__*/React.createElement("img", {
    src: resultAnimated ? `data:image/gif;base64,${result}` : `data:image/png;base64,${result}`,
    style: {
      maxWidth: '100%',
      maxHeight: 220,
      borderRadius: 10,
      border: '2px solid rgba(34,197,94,0.3)'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 8,
      marginTop: 12
    }
  }, /*#__PURE__*/React.createElement("button", {
    style: {
      flex: 1,
      padding: 10,
      borderRadius: 8,
      border: '1px solid rgba(0,0,0,0.1)',
      background: '#f3f4f6',
      color: '#6b7280',
      cursor: 'pointer',
      fontWeight: 700,
      fontSize: 12
    },
    onClick: () => {
      setResult(null);
      setPreview(null);
      setAiMeta(null);
      setResultAnimated(false);
    }
  }, "Try Again"), /*#__PURE__*/React.createElement("button", {
    className: "ai-apply-btn",
    style: {
      flex: 1,
      fontSize: 13,
      padding: 10
    },
    onClick: handleApply
  }, "✅ Apply as Avatar")))));
}
function ActiveSlots({
  effects
}) {
  const slots = [];
  if (effects.flex_effect && effects.flex_effect !== 'title') slots.push({
    slot: 'border',
    label: SLOT_LABELS.border,
    icon: SLOT_ICONS.border
  });
  if (effects.title) slots.push({
    slot: 'title',
    label: `Title: ${effects.title}`,
    icon: SLOT_ICONS.title
  });
  if (effects.name_effect) slots.push({
    slot: 'name',
    label: `Name: ${effects.name_effect}`,
    icon: SLOT_ICONS.name
  });
  if (effects.avatar_border) slots.push({
    slot: 'border',
    label: `Border: ${effects.avatar_border}`,
    icon: SLOT_ICONS.border
  });
  if (effects.bg_effect) slots.push({
    slot: 'avatar',
    label: `Avatar FX: ${effects.bg_effect}`,
    icon: SLOT_ICONS.avatar
  });
  if (!slots.length) return null;
  return /*#__PURE__*/React.createElement("div", {
    className: "active-slots"
  }, slots.map((s, i) => /*#__PURE__*/React.createElement("span", {
    key: i,
    className: `slot-badge ${SLOT_CSS[s.slot] || ''}`
  }, s.icon, " ", s.label)));
}
function InventoryApp() {
  const [items, setItems] = useState([]);
  const [wallet, setWallet] = useState({
    coins: 0,
    gems: 0,
    name_effect: '',
    avatar_border: '',
    bg_effect: '',
    flex_effect: '',
    title: '',
    profile_pic_generations: 0
  });
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState('all');
  const [toast, setToast] = useState(null);
  const [openingCrate, setOpeningCrate] = useState(null);
  const [crateReward, setCrateReward] = useState(null);
  const [showAvatarModal, setShowAvatarModal] = useState(false);
  const [showAIModal, setShowAIModal] = useState(false);
  const showToast = msg => {
    setToast(msg);
    setTimeout(() => setToast(null), 2500);
  };
  const handleAvatarSave = async imgBase64 => {
    try {
      const res = await fetch('/api/shop/avatar-upload/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCSRF()
        },
        body: JSON.stringify({
          image: 'data:image/png;base64,' + imgBase64
        })
      });
      if (res.ok) {
        setWallet(prev => ({
          ...prev,
          has_avatar: true
        }));
        showToast('Avatar updated!');
      } else showAlert('Failed to save avatar');
    } catch (e) {
      showAlert('Save failed');
    }
  };
  const fetchInventory = useCallback(async () => {
    try {
      const [invRes, walletRes] = await Promise.all([fetch('/api/shop/inventory/').then(r => r.json()), fetch('/api/shop/wallet/').then(r => r.json())]);
      setItems(invRes);
      setWallet(walletRes);
    } catch (e) {
      console.error('Failed to load inventory', e);
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => {
    fetchInventory();
  }, [fetchInventory]);
  const toggleItem = async (invId, category, name) => {
    try {
      const res = await fetch('/api/shop/inventory/toggle/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCSRF()
        },
        body: JSON.stringify({
          inventory_id: invId
        })
      });
      if (!res.ok) {
        showToast('Failed to toggle');
        return;
      }
      const data = await res.json();
      setItems(prev => prev.map(i => i.id === invId ? {
        ...i,
        is_active: data.is_active
      } : i));
      fetchInventory();
      if (data.is_active) showToast('Activated!');else showToast('Deactivated');
    } catch (e) {
      showToast('Network error');
    }
  };
  const openCrate = async invId => {
    const item = items.find(i => i.id === invId);
    if (!item) return;
    setOpeningCrate(item);
    setCrateReward(null);
    const startTime = Date.now();
    try {
      const res = await fetch('/api/shop/crate/open/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCSRF()
        },
        body: JSON.stringify({
          inventory_id: invId
        })
      });
      let data;
      try {
        data = await res.json();
      } catch (_) {
        showToast('Server error. Try again.');
        setOpeningCrate(null);
        return;
      }
      if (!res.ok) {
        showToast(data.error || 'Failed to open crate');
        setOpeningCrate(null);
        return;
      }
      const elapsed = Date.now() - startTime;
      const minShake = 2500;
      if (elapsed < minShake) await new Promise(r => setTimeout(r, minShake - elapsed));
      setCrateReward(data.item);
      setItems(prev => prev.filter(i => i.id !== invId));
      fetchInventory();
    } catch (e) {
      showToast('Network error. Check your connection.');
      setOpeningCrate(null);
    }
  };
  const effects = {
    flex_effect: wallet.flex_effect,
    name_effect: wallet.name_effect,
    avatar_border: wallet.avatar_border,
    bg_effect: wallet.bg_effect,
    title: wallet.title
  };
  const previewUser = {
    display_name: wallet.display_name || window.USER.display_name,
    title: wallet.title || window.USER.title,
    has_avatar: wallet.has_avatar != null ? wallet.has_avatar : window.USER.has_avatar
  };
  const grouped = {};
  items.forEach(item => {
    const slot = getSlot(item);
    if (!grouped[slot]) grouped[slot] = [];
    grouped[slot].push(item);
  });
  const filters = [{
    key: 'all',
    label: 'All',
    icon: '📋'
  }, {
    key: 'title',
    label: 'Titles',
    icon: '👑'
  }, {
    key: 'name',
    label: 'Names',
    icon: '✨'
  }, {
    key: 'border',
    label: 'Borders',
    icon: '🔥'
  }, {
    key: 'avatar',
    label: 'Avatar FX',
    icon: '💫'
  }, {
    key: 'boost',
    label: 'Boosts',
    icon: '⚡'
  }, {
    key: 'crate',
    label: 'Crates',
    icon: '📦'
  }];
  const filteredItems = filter === 'all' ? items : items.filter(i => getSlot(i) === filter);
  return /*#__PURE__*/React.createElement("div", {
    style: {
      minHeight: '100vh',
      position: 'relative',
      zIndex: 10,
      pb: 80
    }
  }, /*#__PURE__*/React.createElement("header", {
    style: {
      position: 'sticky',
      top: 0,
      zIndex: 50,
      background: 'linear-gradient(135deg,#fff,#f8fafc)',
      borderBottom: '1px solid rgba(74,158,196,0.15)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      maxWidth: 900,
      margin: '0 auto',
      padding: '12px 16px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between'
    }
  }, /*#__PURE__*/React.createElement("a", {
    href: "/",
    style: {
      display: 'flex',
      alignItems: 'center',
      textDecoration: 'none'
    }
  }, /*#__PURE__*/React.createElement("img", {
    src: "/static/LOGO.png",
    alt: "ChillX",
    style: {
      height: 60,
      width: 'auto'
    }
  })), /*#__PURE__*/React.createElement("h1", {
    style: {
      fontSize: 18,
      fontWeight: 900,
      letterSpacing: 2,
      color: '#2a2a3a'
    }
  }, "CUSTOMIZE"), /*#__PURE__*/React.createElement("div", {
    style: {
      width: 60
    }
  }))), /*#__PURE__*/React.createElement("div", {
    style: {
      maxWidth: 900,
      margin: '0 auto',
      padding: '16px'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      marginBottom: 24
    }
  }, /*#__PURE__*/React.createElement(ProfilePreview, {
    user: previewUser,
    effects: effects,
    onAvatarClick: () => setShowAvatarModal(true),
    inventoryItems: items,
    onToggle: toggleItem
  }), /*#__PURE__*/React.createElement(ActiveSlots, {
    effects: effects
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 8,
      marginTop: 12
    }
  }, /*#__PURE__*/React.createElement("button", {
    onClick: () => setShowAvatarModal(true),
    style: {
      flex: 1,
      padding: '10px 0',
      borderRadius: 10,
      border: '1px solid rgba(74,158,196,0.3)',
      background: '#e8f0f8',
      color: '#4a9ec4',
      fontWeight: 700,
      fontSize: 12,
      cursor: 'pointer',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 6
    }
  }, "📷 Change Avatar"), /*#__PURE__*/React.createElement("button", {
    onClick: () => setShowAIModal(true),
    style: {
      flex: 1,
      padding: '10px 0',
      borderRadius: 10,
      border: '1px solid rgba(245,158,11,0.3)',
      background: '#fff7ed',
      color: '#f59e0b',
      fontWeight: 700,
      fontSize: 12,
      cursor: 'pointer',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 6
    }
  }, "🤖 AI Profile Studio"))), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 8,
      overflowX: 'auto',
      paddingBottom: 8,
      marginBottom: 20
    }
  }, filters.map(f => /*#__PURE__*/React.createElement("button", {
    key: f.key,
    onClick: () => setFilter(f.key),
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 6,
      padding: '8px 16px',
      borderRadius: 10,
      whiteSpace: 'nowrap',
      fontWeight: 700,
      fontSize: 12,
      border: 'none',
      cursor: 'pointer',
      transition: 'all .2s',
      flexShrink: 0,
      background: filter === f.key ? '#e8f0f8' : '#f9fafb',
      color: filter === f.key ? '#4a9ec4' : '#6b7280',
      border: filter === f.key ? '1px solid rgba(74,158,196,0.4)' : '1px solid rgba(0,0,0,0.06)'
    }
  }, /*#__PURE__*/React.createElement("span", null, f.icon), " ", f.label, f.key !== 'all' && grouped[f.key] && /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 10,
      opacity: 0.6
    }
  }, "(", grouped[f.key].length, ")")))), filteredItems.length === 0 ? /*#__PURE__*/React.createElement("div", {
    className: "glass neon-border",
    style: {
      borderRadius: 16,
      padding: '60px 20px',
      textAlign: 'center'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: '3.5rem',
      marginBottom: 16
    }
  }, "📭"), /*#__PURE__*/React.createElement("h2", {
    style: {
      fontSize: 18,
      fontWeight: 800,
      marginBottom: 8
    }
  }, "No items found"), /*#__PURE__*/React.createElement("p", {
    style: {
      color: '#6b7280',
      marginBottom: 24
    }
  }, "Buy items from the shop to see them here!"), /*#__PURE__*/React.createElement("a", {
    href: "/shop/",
    style: {
      display: 'inline-block',
      padding: '10px 28px',
      borderRadius: 12,
      background: 'linear-gradient(135deg,#0d3b66,#4a9ec4)',
      color: '#fff',
      fontWeight: 800,
      textDecoration: 'none',
      fontSize: 13
    }
  }, "🛒 Go to Shop")) : filter === 'all' ? (/* GROUPED BY SLOT */
  Object.entries(grouped).map(([slot, slotItems]) => /*#__PURE__*/React.createElement("div", {
    key: slot,
    style: {
      marginBottom: 28
    }
  }, /*#__PURE__*/React.createElement("div", {
    className: "section-header"
  }, /*#__PURE__*/React.createElement("span", {
    className: "section-icon"
  }, SLOT_ICONS[slot] || '🎁'), /*#__PURE__*/React.createElement("span", {
    className: "section-title"
  }, SLOT_LABELS[slot] || slot), /*#__PURE__*/React.createElement("span", {
    className: "section-count"
  }, slotItems.length)), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fill,minmax(160px,1fr))',
      gap: 12
    }
  }, slotItems.map((item, i) => /*#__PURE__*/React.createElement(ItemCard, {
    key: item.id,
    item: item,
    index: i,
    onToggle: toggleItem,
    onCrate: openCrate,
    crateAnim: openingCrate?.id
  })))))) :
  /*#__PURE__*/
  /* FLAT GRID FOR FILTERED */
  React.createElement("div", {
    style: {
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fill,minmax(160px,1fr))',
      gap: 12
    }
  }, filteredItems.map((item, i) => /*#__PURE__*/React.createElement(ItemCard, {
    key: item.id,
    item: item,
    index: i,
    onToggle: toggleItem,
    onCrate: openCrate,
    crateAnim: openingCrate?.id
  })))), showAvatarModal && /*#__PURE__*/React.createElement(AvatarUploadModal, {
    onClose: () => setShowAvatarModal(false),
    onSave: handleAvatarSave
  }), showAIModal && /*#__PURE__*/React.createElement(AIStudioModal, {
    onClose: () => setShowAIModal(false),
    onSave: handleAvatarSave,
    coins: wallet.coins
  }), openingCrate && /*#__PURE__*/React.createElement(CrateOpenModal, {
    item: openingCrate,
    reward: crateReward,
    onClose: () => {
      setOpeningCrate(null);
      setCrateReward(null);
      fetchInventory();
    }
  }), toast && /*#__PURE__*/React.createElement("div", {
    className: "toast"
  }, toast));
}
function ItemCard({
  item,
  index,
  onToggle,
  onCrate,
  crateAnim
}) {
  const slot = getSlot(item);
  const isCrate = slot === 'crate';
  const isAnimating = crateAnim === item.id;
  return /*#__PURE__*/React.createElement("div", {
    className: `inv-card card-enter ${item.is_active ? 'active' : ''}`,
    style: {
      animationDelay: `${index * 40}ms`
    }
  }, isCrate && isAnimating && /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      background: 'rgba(245,158,11,0.1)',
      borderRadius: 14,
      zIndex: 5,
      animation: 'crateGlow 0.8s ease-in-out'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 6,
      right: 6
    }
  }, /*#__PURE__*/React.createElement("span", {
    className: `slot-badge ${SLOT_CSS[slot] || ''}`,
    style: {
      fontSize: 8,
      padding: '1px 6px'
    }
  }, SLOT_ICONS[slot] || '')), /*#__PURE__*/React.createElement("div", {
    className: `inv-card-icon ${item.rarity === 'legendary' ? '' : ''}`
  }, item.icon || '🎁'), /*#__PURE__*/React.createElement("div", {
    className: "inv-card-name"
  }, item.name), /*#__PURE__*/React.createElement("div", {
    className: `inv-card-rarity rarity-${item.rarity}`
  }, item.rarity), isCrate ? /*#__PURE__*/React.createElement("button", {
    className: "btn-crate",
    onClick: () => onCrate(item.id)
  }, isAnimating ? '⏳ OPENING...' : '📦 OPEN CRATE') : /*#__PURE__*/React.createElement("button", {
    className: `btn-activate ${item.is_active ? 'on' : 'off'}`,
    onClick: () => onToggle(item.id, item.category, item.name)
  }, item.is_active ? '⏸ DEACTIVATE' : '✅ ACTIVATE'));
}
function CrateOpenModal({
  item,
  reward,
  onClose
}) {
  const [phase, setPhase] = useState('loading');
  useEffect(() => {
    if (!item) return;
    setPhase('loading');
  }, [item]);
  useEffect(() => {
    if (reward) {
      setPhase('reveal');
    }
  }, [reward]);
  if (!item) return null;
  const rarColors = {
    common: '#6b7280',
    rare: '#3b82f6',
    epic: '#8b5cf6',
    legendary: '#f59e0b'
  };
  const rarGlows = {
    common: '0 0 40px rgba(107,114,128,0.4)',
    rare: '0 0 40px rgba(59,130,246,0.4)',
    epic: '0 0 40px rgba(139,92,246,0.4)',
    legendary: '0 0 60px rgba(245,158,11,0.5)'
  };
  return /*#__PURE__*/React.createElement("div", {
    className: "fixed inset-0 z-[99999] flex items-center justify-center overflow-hidden",
    style: {
      background: reward ? `radial-gradient(ellipse at center, ${rarColors[reward.rarity]}44 0%, #000 80%)` : '#000',
      transition: 'background 0.6s ease'
    }
  }, /*#__PURE__*/React.createElement("div", {
    className: "relative z-10 text-center px-6 max-w-lg mx-auto"
  }, phase === 'loading' && /*#__PURE__*/React.createElement("div", {
    className: "flex flex-col items-center gap-8"
  }, /*#__PURE__*/React.createElement("div", {
    className: "relative"
  }, /*#__PURE__*/React.createElement("div", {
    className: "text-8xl md:text-9xl",
    style: {
      animation: 'crateShake3 0.1s ease-in-out infinite alternate',
      filter: 'brightness(1.2)'
    }
  }, "📦"), /*#__PURE__*/React.createElement("div", {
    className: "absolute inset-0 flex items-center justify-center"
  }, /*#__PURE__*/React.createElement("div", {
    className: "w-32 h-32 rounded-full",
    style: {
      background: 'radial-gradient(circle, rgba(245,158,11,0.3) 0%, transparent 70%)',
      animation: 'cratePulse 1s ease-in-out infinite'
    }
  }))), /*#__PURE__*/React.createElement("div", {
    className: "flex gap-2"
  }, [0, 1, 2, 3, 4, 5].map(i => /*#__PURE__*/React.createElement("div", {
    key: i,
    className: "w-2.5 h-2.5 rounded-full",
    style: {
      background: `hsl(${200 + i * 12},70%,50%)`,
      animation: `crateDot2 0.6s ease-in-out ${i * 0.12}s infinite alternate`
    }
  }))), /*#__PURE__*/React.createElement("p", {
    className: "text-gray-400 text-sm tracking-[6px] uppercase font-bold animate-pulse"
  }, "Unlocking...")), phase === 'reveal' && reward && /*#__PURE__*/React.createElement("div", {
    className: "flex flex-col items-center gap-5",
    style: {
      animation: 'crateReveal2 0.7s cubic-bezier(0.16,1,0.3,1) both'
    }
  }, /*#__PURE__*/React.createElement("div", {
    className: "absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-72 h-72 rounded-full pointer-events-none",
    style: {
      background: `radial-gradient(circle, ${rarColors[reward.rarity]}55 0%, transparent 70%)`,
      animation: 'crateBurst 1.5s ease-out infinite'
    }
  }), /*#__PURE__*/React.createElement("div", {
    className: "text-[10px] font-black uppercase tracking-[6px] px-6 py-2 rounded-full border",
    style: {
      color: rarColors[reward.rarity],
      borderColor: `${rarColors[reward.rarity]}44`,
      background: `${rarColors[reward.rarity]}15`,
      boxShadow: `0 0 20px ${rarColors[reward.rarity]}22`
    }
  }, "★ ", reward.rarity, " drop ★"), /*#__PURE__*/React.createElement("div", {
    className: "relative"
  }, /*#__PURE__*/React.createElement("div", {
    className: "text-7xl md:text-8xl",
    style: {
      filter: `drop-shadow(0 0 40px ${rarColors[reward.rarity]}66)`,
      animation: 'crateFloat 2s ease-in-out infinite'
    }
  }, reward.icon || '🎁')), /*#__PURE__*/React.createElement("div", {
    className: "text-2xl md:text-3xl font-black tracking-tight",
    style: {
      color: rarColors[reward.rarity],
      textShadow: `0 0 40px ${rarColors[reward.rarity]}44`
    }
  }, reward.name), reward.description && /*#__PURE__*/React.createElement("div", {
    className: "text-sm text-gray-400 max-w-xs leading-relaxed"
  }, reward.description), /*#__PURE__*/React.createElement("div", {
    className: "w-40 h-[2px] rounded-full",
    style: {
      background: `linear-gradient(90deg, transparent, ${rarColors[reward.rarity]}, transparent)`
    }
  }), /*#__PURE__*/React.createElement("button", {
    onClick: onClose,
    className: "relative mt-2 px-10 py-3.5 rounded-xl font-bold text-base uppercase tracking-widest transition-all duration-300 hover:scale-105 active:scale-95 overflow-hidden",
    style: {
      background: `linear-gradient(135deg, ${rarColors[reward.rarity]}, ${rarColors[reward.rarity]}bb)`,
      color: '#fff',
      boxShadow: rarGlows[reward.rarity]
    }
  }, /*#__PURE__*/React.createElement("span", {
    className: "relative z-10"
  }, reward.rarity === 'legendary' ? '👑 LEGENDARY!' : '🔥 CLAIM'), /*#__PURE__*/React.createElement("div", {
    className: "absolute inset-0",
    style: {
      background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent)',
      transform: 'skewX(-20deg) translateX(-100%)',
      animation: 'crateShine 2s ease-in-out infinite'
    }
  })))), /*#__PURE__*/React.createElement("style", null, `
        @keyframes crateShake3{0%{transform:translateX(-12px) rotate(-8deg) scale(1.03)}100%{transform:translateX(12px) rotate(8deg) scale(0.97)}}
        @keyframes cratePulse{0%,100%{transform:scale(0.8);opacity:0.3}50%{transform:scale(1.5);opacity:0.6}}
        @keyframes crateDot2{0%{opacity:0.2;transform:scale(0.7) translateY(0)}100%{opacity:1;transform:scale(1.3) translateY(-8px)}}
        @keyframes crateReveal2{0%{opacity:0;transform:scale(0.2) rotateY(120deg);filter:blur(10px)}60%{filter:blur(2px)}100%{opacity:1;transform:scale(1) rotateY(0deg);filter:blur(0)}}
        @keyframes crateBurst{0%,100%{transform:translate(-50%,-50%) scale(1);opacity:0.4}50%{transform:translate(-50%,-50%) scale(1.8);opacity:0.1}}
        @keyframes crateFloat{0%,100%{transform:translateY(0)}50%{transform:translateY(-8px)}}
        @keyframes crateShine{0%{transform:skewX(-20deg) translateX(-100%)}100%{transform:skewX(-20deg) translateX(200%)}}
      `));
}
const root = createRoot(document.getElementById('root'));
root.render(/*#__PURE__*/React.createElement(InventoryApp, null));