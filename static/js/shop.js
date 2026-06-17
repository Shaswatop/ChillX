const {
  useState,
  useEffect,
  useRef,
  useCallback,
  useMemo
} = React;

// ── CONFIG ──
const API = {
  items: '/api/shop/items/',
  featured: '/api/shop/items/featured/',
  buy: '/api/shop/buy/',
  inventory: '/api/shop/inventory/',
  wallet: '/api/shop/wallet/',
  raffle: '/api/shop/raffle/current/',
  raffleBuy: '/api/shop/raffle/buy/',
  recent: '/api/shop/recent/'
};
const RARITY_COLORS = {
  common: '#6b7280',
  rare: '#3b82f6',
  epic: '#8b5cf6',
  legendary: '#f59e0b'
};
const RARITY_BG = {
  common: 'bg-gray-500/10',
  rare: 'bg-blue-500/10',
  epic: 'bg-purple-500/10',
  legendary: 'bg-amber-500/10'
};
const RARITY_TEXT = {
  common: 'text-gray-400',
  rare: 'text-blue-400',
  epic: 'text-purple-400',
  legendary: 'text-amber-400'
};
const EFFECT_TO_PREVIEW = {
  'flame-border': 'flame-border',
  'electric-border': 'electric-border',
  'shooting-stars': 'shooting-stars',
  'blood-moon': 'blood-moon',
  'void': 'void-card',
  'holo': 'holo-card',
  'matrix': 'matrix-card',
  'angel': 'angel-card',
  'demon': 'demon-card',
  'galaxy': 'galaxy-card',
  'neon': 'neon-card',
  'cyber': 'cyber-card',
  'sakura': 'sakura-card',
  'lava': 'lava-card',
  'shadow': 'shadow-card',
  'thunder': 'thunder-card',
  'ring': 'ring-card',
  'cursed': 'cursed-card',
  'crypto': 'crypto-card',
  'pixel': 'pixel-card',
  'dragon': 'dragon-card',
  'sunrise': 'sunrise-card',
  'overload': 'overload-card',
  'bounty': 'bounty-card',
  'frost': 'frostbite-card',
  'ice': 'ice-border',
  'title': 'title-glow',
  '': ''
};

// ── CURRENCY DISPLAY ──
function AnimatedNumber({
  value,
  prefix = '',
  suffix = '',
  className = '',
  style = {}
}) {
  const [display, setDisplay] = useState(value);
  const animRef = useRef(null);
  useEffect(() => {
    const from = display;
    const to = value;
    if (from === to) return;
    const dur = 600;
    const start = performance.now();
    const tick = now => {
      const t = Math.min((now - start) / dur, 1);
      const eased = 1 - Math.pow(1 - t, 3);
      setDisplay(Math.round(from + (to - from) * eased));
      if (t < 1) animRef.current = requestAnimationFrame(tick);
    };
    animRef.current = requestAnimationFrame(tick);
    return () => animRef.current && cancelAnimationFrame(animRef.current);
  }, [value]);
  return /*#__PURE__*/React.createElement("span", {
    className: className,
    style: style
  }, prefix, display.toLocaleString(), suffix);
}
const CoinIcon = ({
  size = 16
}) => /*#__PURE__*/React.createElement("img", {
  src: "/static/cash.png",
  alt: "",
  style: {
    width: size,
    height: size,
    display: 'inline',
    verticalAlign: 'middle',
    objectFit: 'contain',
    margin: '-2px 2px 0 0'
  }
});
const GemIcon = ({
  size = 16
}) => /*#__PURE__*/React.createElement("img", {
  src: "/static/diamond.png",
  alt: "",
  style: {
    width: size,
    height: size,
    display: 'inline',
    verticalAlign: 'middle',
    objectFit: 'contain',
    margin: '-2px 2px 0 0'
  }
});
function WalletBar({
  wallet,
  onCoinChange
}) {
  const [shake, setShake] = useState(false);
  const prevCoins = useRef(wallet.coins);
  useEffect(() => {
    if (wallet.coins < prevCoins.current) {
      setShake(true);
      setTimeout(() => setShake(false), 400);
    }
    prevCoins.current = wallet.coins;
  }, [wallet.coins]);
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: '10px'
    }
  }, /*#__PURE__*/React.createElement("div", {
    className: `${shake ? 'shake' : ''}`,
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: '8px',
      padding: '8px 18px',
      borderRadius: '12px',
      background: 'rgba(74,158,196,0.15)',
      border: '1.5px solid rgba(74,158,196,0.3)'
    }
  }, /*#__PURE__*/React.createElement("img", {
    src: "/static/cash.png",
    alt: "money",
    style: {
      width: '28px',
      height: '28px',
      objectFit: 'contain'
    }
  }), /*#__PURE__*/React.createElement(AnimatedNumber, {
    value: wallet.coins,
    className: "font-bold text-xl min-w-[44px] text-right",
    style: {
      color: 'var(--ink)',
      fontWeight: 800
    }
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: '8px',
      padding: '8px 18px',
      borderRadius: '12px',
      background: 'rgba(168,85,247,0.15)',
      border: '1.5px solid rgba(168,85,247,0.3)'
    }
  }, /*#__PURE__*/React.createElement("img", {
    src: "/static/diamond.png",
    alt: "gems",
    style: {
      width: '26px',
      height: '26px',
      objectFit: 'contain'
    }
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      fontWeight: 800,
      fontSize: '1.15rem',
      color: '#7c3aed'
    }
  }, wallet.gems)));
}

// ── TOAST ──
let toastTimeout;
function showToast(msg, duration = 3000) {
  const el = document.getElementById('toastContainer');
  if (!el) return;
  el.textContent = msg;
  el.style.display = 'block';
  clearTimeout(toastTimeout);
  requestAnimationFrame(() => {
    el.classList.add('show');
  });
  toastTimeout = setTimeout(() => {
    el.classList.remove('show');
    setTimeout(() => {
      el.style.display = 'none';
    }, 400);
  }, duration);
}

// ── CONFETTI ──
function burstConfetti() {
  const colors = ['#0d3b66', '#4a9ec4', '#f59e0b', '#ec4899', '#3b82f6', '#14b8a6', '#22c55e'];
  for (let i = 0; i < 40; i++) {
    const c = document.createElement('div');
    c.className = 'confetti-piece';
    c.style.background = colors[Math.floor(Math.random() * colors.length)];
    c.style.left = 20 + Math.random() * 60 + '%';
    c.style.top = 20 + Math.random() * 30 + '%';
    c.style.width = 4 + Math.random() * 6 + 'px';
    c.style.height = 4 + Math.random() * 6 + 'px';
    c.style.animationDuration = 1 + Math.random() * 1.5 + 's';
    c.style.animationDelay = Math.random() * 0.3 + 's';
    document.body.appendChild(c);
    setTimeout(() => c.remove(), 2500);
  }
}

// ── COIN FLY ──
function coinFly(fromEl, toEl) {
  if (!fromEl || !toEl) return;
  const from = fromEl.getBoundingClientRect();
  const to = toEl.getBoundingClientRect();
  const dx = to.left - from.left;
  const dy = to.top - from.top;
  for (let i = 0; i < 6; i++) {
    const c = document.createElement('div');
    c.className = 'coin-fly';
    c.innerHTML = '<img src="/static/cash.png" alt="" style="width:20px;height:20px;object-fit:contain;pointer-events:none">';
    c.style.left = from.left + from.width / 2 + 'px';
    c.style.top = from.top + from.height / 2 + 'px';
    c.style.setProperty('--tx', dx + (Math.random() - 0.5) * 60 + 'px');
    c.style.setProperty('--ty', dy + (Math.random() - 0.5) * 40 + 'px');
    c.style.animationDelay = i * 0.05 + 's';
    document.body.appendChild(c);
    setTimeout(() => c.remove(), 1000);
  }
}

// ── COUNTDOWN ──
function CountdownTimer({
  expiresAt
}) {
  const [remaining, setRemaining] = useState(0);
  useEffect(() => {
    if (!expiresAt) return;
    const target = new Date(expiresAt).getTime();
    const tick = () => {
      const diff = Math.max(0, Math.floor((target - Date.now()) / 1000));
      setRemaining(diff);
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [expiresAt]);
  if (!expiresAt || remaining <= 0) return null;
  const h = String(Math.floor(remaining / 3600)).padStart(2, '0');
  const m = String(Math.floor(remaining % 3600 / 60)).padStart(2, '0');
  const s = String(remaining % 60).padStart(2, '0');
  return /*#__PURE__*/React.createElement("span", {
    className: "countdown text-xs text-red-400 font-mono"
  }, "⏰ ", h, ":", m, ":", s);
}

// ── FLEX PREVIEW ──
const FLEX_PREVIEW_CLASSES = {
  'Flame Profile Border': 'flame-border',
  'Electric Profile Border': 'electric-border',
  'Shooting Star Effect': 'shooting-stars',
  'Ice Border': 'ice-border',
  'Blood Moon': 'blood-moon',
  'Blood Moon Effect': 'blood-moon',
  'Void': 'void-card',
  'Void Effect': 'void-card',
  'Holographic': 'holo-card',
  'Holographic Name': 'holo-card',
  'Matrix Rain': 'matrix-card',
  'Matrix': 'matrix-card',
  'Angel': 'angel-card',
  'Angel Effect': 'angel-card',
  'Demon': 'demon-card',
  'Demon Effect': 'demon-card',
  'Galaxy': 'galaxy-card',
  'Galaxy Effect': 'galaxy-card',
  'Neon Sign': 'neon-card',
  'Neon': 'neon-card',
  'Cyberpunk': 'cyber-card',
  'Cyberpunk Effect': 'cyber-card',
  'Sakura': 'sakura-card',
  'Sakura Effect': 'sakura-card',
  'Lava': 'lava-card',
  'Lava Effect': 'lava-card',
  'Shadow': 'shadow-card',
  'Shadow Effect': 'shadow-card',
  'Thunder': 'thunder-card',
  'Thunder Effect': 'thunder-card',
  'Ring Spinner': 'ring-card',
  'Saturn Ring': 'ring-card',
  'Cursed': 'cursed-card',
  'Cursed Effect': 'cursed-card',
  'Crypto Ticker': 'crypto-card',
  'Crypto': 'crypto-card',
  'Pixel': 'pixel-card',
  '8-Bit': 'pixel-card',
  'Pixel Name': 'pixel-card',
  'Dragon': 'dragon-card',
  'Dragon Effect': 'dragon-card',
  'Sunrise': 'sunrise-card',
  'Sunrise Effect': 'sunrise-card',
  'Overloaded': 'overload-card',
  'Overload': 'overload-card',
  'Bounty Hunter': 'bounty-card',
  'Bounty': 'bounty-card',
  'Frostbite': 'frostbite-card',
  'Frostbite Effect': 'frostbite-card',
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
  'Mystic Mist': 'mystic-mist',
  'Stardust Burst': 'stardust',
  'Ember Sparks': 'ember-sparks',
  'Snowfall': 'snowfall',
  'Energy Arc': 'energy-arc',
  'Neon Rain': 'neon-rain',
  'Spirit Orbs': 'spirit-orbs'
};
function getFlexClass(name) {
  for (const [key, cls] of Object.entries(FLEX_PREVIEW_CLASSES)) {
    if (name.includes(key)) return cls;
  }
  return null;
}
function FlexPreview({
  name,
  compact
}) {
  const cls = getFlexClass(name);
  if (!cls) return /*#__PURE__*/React.createElement("div", {
    className: "text-4xl text-center mb-3"
  }, "👑");
  const isBorder = cls.includes('border') || ['ice-border', 'cyber-card', 'thunder-card', 'ring-card', 'crypto-card', 'bounty-card', 'shadow-card', 'cursed-card', 'void-card', 'blood-moon', 'demon-card', 'dragon-card', 'lava-card', 'overload-card', 'frostbite-card', 'sunrise-card'].includes(cls);
  const isName = !isBorder && !['shooting-stars', 'sakura-card', 'matrix-card', 'holo-card', 'galaxy-card', 'angel-card', 'neon-card', 'pixel-card', 'crypto-card', 'bounty-card'].includes(cls);
  const className = compact ? 'preview-card-inline' : 'preview-card';
  const avatarSize = compact ? '24px' : '36px';
  const usernameSize = compact ? '11px' : '13px';
  const extras = {};
  if (cls === 'shooting-stars') {
    extras.stars = true;
  } else if (cls === 'sakura-card') {
    extras.petals = true;
  } else if (cls === 'matrix-card') {
    extras.matrix = true;
  } else if (cls === 'crypto-card') {
    extras.crypto = true;
  }
  const effectCls = cls;
  const sizeStyle = compact ? {
    padding: '8px',
    borderRadius: '8px',
    borderWidth: '1.5px'
  } : {
    padding: '14px',
    borderRadius: '12px'
  };
  return /*#__PURE__*/React.createElement("div", {
    className: `${effectCls}`,
    style: {
      ...sizeStyle,
      position: 'relative',
      overflow: 'hidden',
      background: '#0f0f1a',
      border: '1.5px solid #1e1e30',
      marginBottom: compact ? '4px' : '10px'
    }
  }, extras.stars && /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("div", {
    className: "star-dot",
    style: {
      top: '15%',
      left: '10%',
      '--dur': '1.2s',
      '--delay': '0s'
    }
  }), /*#__PURE__*/React.createElement("div", {
    className: "star-dot",
    style: {
      top: '70%',
      left: '80%',
      '--dur': '1.8s',
      '--delay': '0.3s'
    }
  }), /*#__PURE__*/React.createElement("div", {
    className: "star-dot",
    style: {
      top: '40%',
      left: '60%',
      '--dur': '1.4s',
      '--delay': '0.7s'
    }
  }), /*#__PURE__*/React.createElement("div", {
    className: "shooting-trail",
    style: {
      top: '20%',
      left: '5%',
      '--delay': '0s'
    }
  })), extras.petals && /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("div", {
    className: "sakura-petal",
    style: {
      left: '10%',
      '--dur': '2s',
      '--d': '0s'
    }
  }, "🌸"), /*#__PURE__*/React.createElement("div", {
    className: "sakura-petal",
    style: {
      left: '30%',
      '--dur': '2.5s',
      '--d': '0.4s'
    }
  }, "🌸"), /*#__PURE__*/React.createElement("div", {
    className: "sakura-petal",
    style: {
      left: '60%',
      '--dur': '1.8s',
      '--d': '0.8s'
    }
  }, "🌸")), extras.crypto && /*#__PURE__*/React.createElement("div", {
    className: "crypto-ticker"
  }, /*#__PURE__*/React.createElement("span", null, "🟢 XP +2.4% | 🔴 RANK -1 | 🟢 STREAK +5")), /*#__PURE__*/React.createElement("div", {
    className: `card-preview-top`,
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: '8px',
      position: 'relative',
      zIndex: 1
    }
  }, /*#__PURE__*/React.createElement("div", {
    className: `preview-avatar ${cls === 'ring-card' ? cls : ''}`,
    style: {
      width: avatarSize,
      height: avatarSize,
      borderRadius: '50%',
      background: '#1a1a2e',
      border: '2px solid #2a2a40',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontSize: parseInt(avatarSize) * 0.5 + 'px',
      flexShrink: 0,
      position: 'relative',
      overflow: 'hidden'
    }
  }, cls.includes('flame') ? '🔥' : cls.includes('electric') ? '⚡' : '🛡️'), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      minWidth: 0
    }
  }, /*#__PURE__*/React.createElement("div", {
    className: "preview-username",
    style: {
      fontSize: usernameSize,
      fontWeight: 700,
      letterSpacing: '0.5px',
      color: '#e0e0ff'
    }
  }, "SHASWAT"), /*#__PURE__*/React.createElement("div", {
    className: "preview-tag",
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: '3px',
      fontSize: '8px',
      fontWeight: 700,
      letterSpacing: '1px',
      padding: '1px 6px',
      borderRadius: '3px',
      marginTop: '2px',
      background: '#1a1a2e',
      border: '1px solid #2a2a40',
      color: '#9ca3af'
    }
  }, name.includes('Title') ? '👑 TITLE' : cls.includes('flame') ? '🔥 FLAME' : cls.includes('electric') ? '⚡ ELECTRIC' : cls.includes('moon') ? '🩸 BLOOD' : cls.includes('void') ? '🕳️ VOID' : cls.includes('holo') ? '💿 HOLO' : cls.includes('matrix') ? '👾 MATRIX' : cls.includes('angel') ? '😇 ANGEL' : cls.includes('demon') ? '😈 DEMON' : cls.includes('galaxy') ? '🌌 GALAXY' : cls.includes('neon') ? '💡 NEON' : cls.includes('cyber') ? '🦾 CYBER' : cls.includes('sakura') ? '🌸 SAKURA' : cls.includes('lava') ? '🌋 LAVA' : cls.includes('shadow') ? '🌑 SHADOW' : cls.includes('thunder') ? '⛈️ THUNDER' : cls.includes('ring') ? '🪐 RING' : cls.includes('cursed') ? '🫠 CURSED' : cls.includes('crypto') ? '📈 CRYPTO' : cls.includes('pixel') ? '🕹️ PIXEL' : cls.includes('dragon') ? '🐉 DRAGON' : cls.includes('sunrise') ? '🌅 SUNRISE' : cls.includes('overload') ? '💥 OVERLOAD' : cls.includes('bounty') ? '🤠 BOUNTY' : cls.includes('frost') ? '🧊 FROST' : cls.includes('ice') ? '❄️ ICE' : '✨ FLEX'))), extras.matrix && /*#__PURE__*/React.createElement("div", {
    className: "absolute inset-0 opacity-[0.08] pointer-events-none overflow-hidden",
    style: {
      fontFamily: 'monospace',
      fontSize: '8px',
      color: '#4ade80',
      lineHeight: '12px',
      whiteSpace: 'pre'
    }
  }, '01'.repeat(40)));
}

// ── ITEM CARD ──
function ItemCard({
  item,
  wallet,
  onBuy,
  onOpenCrate,
  index
}) {
  const rarity = item.rarity || 'common';
  const isLegendary = rarity === 'legendary';
  const isOwned = item.owned;
  const isGem = item.price_gems > 0;
  const cost = isGem ? item.price_gems : item.sale_price;
  const canAfford = isGem ? wallet.gems >= cost : wallet.coins >= cost;
  const needMore = cost - (isGem ? wallet.gems : wallet.coins);
  const isLimited = item.is_limited && item.stock_remaining > 0 && item.stock_remaining < 20;
  const isCrate = item.category === 'lootbox';
  const cardRef = useRef(null);
  const handleBuyClick = () => {
    if (isOwned || !canAfford) return;
    onBuy(item, cardRef.current, isGem ? 'gems' : 'coins');
  };
  const handleOpen = () => {
    if (onOpenCrate) onOpenCrate(item, cardRef.current);
  };
  return /*#__PURE__*/React.createElement("div", {
    ref: cardRef,
    className: `shop-card card-enter sr sr-scale ${rarity}${isLegendary ? ' shimmer-gold' : ''}${isOwned ? ' opacity-60' : ' cursor-pointer'}`,
    style: {
      animationDelay: index * 0.06 + 's',
      borderColor: isOwned ? 'rgba(34,197,94,0.25)' : `${RARITY_COLORS[rarity]}22`
    }
  }, /*#__PURE__*/React.createElement("div", {
    className: "absolute top-5 right-4 flex flex-col items-end gap-1.5 z-10"
  }, item.discount_percent > 0 && /*#__PURE__*/React.createElement("span", {
    style: {
      background: 'linear-gradient(135deg,#ef4444,#dc2626)',
      color: '#fff',
      fontSize: '10px',
      fontWeight: 800,
      padding: '3px 10px',
      borderRadius: '999px',
      boxShadow: '0 2px 6px rgba(239,68,68,0.3)',
      letterSpacing: '0.5px'
    }
  }, "-", item.discount_percent, "%"), isOwned && /*#__PURE__*/React.createElement("span", {
    style: {
      background: 'rgba(34,197,94,0.15)',
      color: '#16a34a',
      fontSize: '10px',
      fontWeight: 800,
      padding: '3px 10px',
      borderRadius: '999px',
      border: '1.5px solid rgba(34,197,94,0.25)',
      letterSpacing: '0.3px'
    }
  }, "✓ Owned")), isLimited && /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: '-4px',
      left: '-4px',
      background: 'linear-gradient(135deg,#f59e0b,#f97316)',
      color: '#fff',
      fontSize: '9px',
      fontWeight: 800,
      padding: '3px 10px',
      borderRadius: '999px',
      zIndex: 10,
      boxShadow: '0 2px 6px rgba(245,158,11,0.3)'
    }
  }, "🔥 ", item.stock_remaining, " left"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      justifyContent: 'center',
      marginBottom: '12px'
    }
  }, item.category === 'flex' ? /*#__PURE__*/React.createElement(FlexPreview, {
    name: item.name,
    compact: true
  }) : /*#__PURE__*/React.createElement("div", {
    style: {
      width: '72px',
      height: '72px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      borderRadius: '16px',
      background: `${RARITY_COLORS[rarity]}10`,
      border: `1.5px solid ${RARITY_COLORS[rarity]}20`,
      fontSize: '2rem',
      transition: 'all .3s ease'
    },
    className: isLegendary ? 'animate-pulse' : ''
  }, item.icon || '🎁')), /*#__PURE__*/React.createElement("div", {
    style: {
      color: RARITY_COLORS[rarity],
      fontSize: '9px',
      fontWeight: 800,
      textTransform: 'uppercase',
      letterSpacing: '1.5px',
      marginBottom: '6px',
      display: 'flex',
      alignItems: 'center',
      gap: '5px'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      width: '6px',
      height: '6px',
      borderRadius: '50%',
      background: RARITY_COLORS[rarity],
      boxShadow: `0 0 6px ${RARITY_COLORS[rarity]}`
    }
  }), rarity), /*#__PURE__*/React.createElement("h3", {
    style: {
      fontWeight: 800,
      fontSize: '.95rem',
      color: 'var(--teal-2)',
      marginBottom: '4px',
      lineHeight: '1.3'
    }
  }, item.name), /*#__PURE__*/React.createElement("p", {
    style: {
      fontSize: '.78rem',
      color: 'rgba(42,42,58,0.45)',
      marginBottom: '16px',
      lineHeight: '1.4',
      minHeight: '2.2em'
    }
  }, item.description || '...'), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: '8px',
      marginBottom: '16px',
      padding: '8px 12px',
      background: 'rgba(0,0,0,0.02)',
      borderRadius: '10px',
      border: '1px solid rgba(0,0,0,0.04)'
    }
  }, item.discount_percent > 0 && /*#__PURE__*/React.createElement("span", {
    style: {
      color: 'rgba(42,42,58,0.3)',
      fontSize: '.8rem',
      textDecoration: 'line-through'
    }
  }, item.price_coins, " ", /*#__PURE__*/React.createElement(CoinIcon, null)), isGem ? /*#__PURE__*/React.createElement("span", {
    style: {
      fontWeight: 800,
      fontSize: '1rem',
      color: '#9333ea'
    }
  }, /*#__PURE__*/React.createElement(GemIcon, {
    size: 16
  }), " ", item.price_gems) : /*#__PURE__*/React.createElement("span", {
    style: {
      fontWeight: 800,
      fontSize: '1rem',
      color: '#d97706'
    }
  }, /*#__PURE__*/React.createElement(CoinIcon, {
    size: 16
  }), " ", item.sale_price)), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 'auto'
    }
  }, item.name === 'AI Profile Pic Generator' && isOwned ? /*#__PURE__*/React.createElement("a", {
    href: "/inventory/",
    className: "game-btn game-btn-primary",
    style: {
      width: '100%',
      justifyContent: 'center',
      padding: '10px 0',
      fontSize: '.8rem'
    }
  }, "🎨 USE IN INVENTORY") : isCrate && isOwned ? /*#__PURE__*/React.createElement("button", {
    onClick: handleOpen,
    className: "game-btn game-btn-gold",
    style: {
      width: '100%',
      justifyContent: 'center',
      padding: '10px 0',
      fontSize: '.8rem'
    }
  }, "📦 OPEN CRATE") : /*#__PURE__*/React.createElement("button", {
    onClick: handleBuyClick,
    disabled: isOwned || !canAfford,
    className: "game-btn",
    style: {
      width: '100%',
      justifyContent: 'center',
      padding: '10px 0',
      fontSize: '.8rem',
      cursor: isOwned || !canAfford ? 'not-allowed' : 'pointer',
      ...(isOwned ? {
        background: 'rgba(34,197,94,0.1)',
        color: '#16a34a',
        border: '1.5px solid rgba(34,197,94,0.2)'
      } : canAfford ? {
        background: 'linear-gradient(135deg,#134166,#1a5a8a)',
        color: '#fff',
        boxShadow: '0 4px 12px rgba(13,59,102,0.3)'
      } : {
        background: 'rgba(0,0,0,0.04)',
        color: 'rgba(0,0,0,0.3)',
        border: '1.5px solid rgba(0,0,0,0.06)'
      })
    },
    onMouseOver: e => {
      if (canAfford && !isOwned) e.currentTarget.style.background = 'linear-gradient(135deg,#1a5a8a,#1f6a9a)';
    },
    onMouseOut: e => {
      if (canAfford && !isOwned) e.currentTarget.style.background = 'linear-gradient(135deg,#134166,#1a5a8a)';
    }
  }, isOwned ? '✓ Owned' : canAfford ? isGem ? /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement(GemIcon, {
    size: 14
  }), " ", cost) : /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement(CoinIcon, null), " ", cost) : /*#__PURE__*/React.createElement(React.Fragment, null, "Need ", needMore, " more ", isGem ? /*#__PURE__*/React.createElement(GemIcon, {
    size: 14
  }) : /*#__PURE__*/React.createElement(CoinIcon, null)))));
}

// ── FEATURED CAROUSEL ──
function FeaturedCarousel({
  items,
  wallet,
  onBuy,
  onOpenCrate
}) {
  const [current, setCurrent] = useState(0);
  const len = items.length;
  const item = items[current];
  const isGem = item?.price_gems > 0;
  const intervalRef = useRef(null);
  useEffect(() => {
    if (len <= 1) return;
    intervalRef.current = setInterval(() => {
      setCurrent(p => (p + 1) % len);
    }, 6000);
    return () => clearInterval(intervalRef.current);
  }, [len]);
  if (!len) return null;
  return /*#__PURE__*/React.createElement("div", {
    className: "relative overflow-hidden rounded-2xl mb-6",
    style: {
      minHeight: 280,
      background: '#fff',
      border: '2px solid var(--teal-2)',
      boxShadow: '0 4px 20px rgba(0,0,0,0.06)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    className: "absolute inset-0",
    style: {
      background: 'linear-gradient(135deg, rgba(13,59,102,0.03), transparent, rgba(74,158,196,0.02))'
    }
  }), item.rarity === 'legendary' && /*#__PURE__*/React.createElement("div", {
    className: "absolute inset-0",
    style: {
      background: 'linear-gradient(90deg, transparent, rgba(245,158,11,0.04), transparent)',
      animation: 'shimmer 2s ease-in-out infinite'
    }
  }), /*#__PURE__*/React.createElement("div", {
    className: "relative p-6 md:p-8 flex flex-col md:flex-row items-center gap-5"
  }, /*#__PURE__*/React.createElement("div", {
    className: `text-6xl md:text-7xl ${item.rarity === 'legendary' ? 'float' : ''}`
  }, item.icon || '🎁'), /*#__PURE__*/React.createElement("div", {
    className: "flex-1"
  }, /*#__PURE__*/React.createElement("div", {
    className: "flex items-center gap-3 mb-2 flex-wrap"
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      color: RARITY_COLORS[item.rarity],
      fontSize: '11px',
      fontWeight: 700,
      textTransform: 'uppercase',
      letterSpacing: '1.5px',
      padding: '3px 12px',
      borderRadius: '999px',
      border: `1.5px solid ${RARITY_COLORS[item.rarity]}44`,
      background: `${RARITY_COLORS[item.rarity]}15`
    }
  }, "★ FEATURED ", item.rarity?.toUpperCase()), /*#__PURE__*/React.createElement(CountdownTimer, {
    expiresAt: item.expires_at
  })), /*#__PURE__*/React.createElement("h2", {
    className: "text-xl md:text-2xl font-black mb-2",
    style: {
      color: 'var(--teal-2)'
    }
  }, item.name), /*#__PURE__*/React.createElement("p", {
    className: "mb-3",
    style: {
      color: 'var(--ink)',
      opacity: 0.6,
      fontSize: '.85rem'
    }
  }, item.description || 'Limited time offer!'), /*#__PURE__*/React.createElement("div", {
    className: "flex items-center gap-4 mb-4"
  }, item.discount_percent > 0 && /*#__PURE__*/React.createElement("span", {
    style: {
      color: 'rgba(42,42,58,0.35)',
      textDecoration: 'line-through',
      fontSize: '1rem'
    }
  }, item.price_coins, " ", /*#__PURE__*/React.createElement(CoinIcon, {
    size: 16
  })), isGem ? /*#__PURE__*/React.createElement("span", {
    className: "text-2xl font-bold",
    style: {
      color: '#c084fc'
    }
  }, /*#__PURE__*/React.createElement(GemIcon, {
    size: 20
  }), " ", item.price_gems) : /*#__PURE__*/React.createElement("span", {
    className: "text-2xl font-bold",
    style: {
      color: '#f59e0b'
    }
  }, /*#__PURE__*/React.createElement(CoinIcon, {
    size: 20
  }), " ", item.sale_price)), item.category === 'lootbox' && item.owned ? /*#__PURE__*/React.createElement("button", {
    onClick: () => onOpenCrate(item, document.querySelector('.featured-cta')),
    className: "featured-cta game-btn game-btn-gold",
    style: {
      padding: '12px 32px'
    }
  }, "📦 OPEN CRATE") : /*#__PURE__*/React.createElement("button", {
    onClick: () => onBuy(item, document.querySelector('.featured-cta'), isGem ? 'gems' : 'coins'),
    disabled: item.owned || (isGem ? wallet.gems < item.price_gems : wallet.coins < item.sale_price),
    className: "featured-cta game-btn",
    style: {
      padding: '12px 32px',
      cursor: item.owned || (isGem ? wallet.gems < item.price_gems : wallet.coins < item.sale_price) ? 'not-allowed' : 'pointer',
      ...(item.owned ? {
        background: 'rgba(34,197,94,0.1)',
        color: '#16a34a',
        border: '1.5px solid rgba(34,197,94,0.2)'
      } : (isGem ? wallet.gems >= item.price_gems : wallet.coins >= item.sale_price) ? {
        background: 'linear-gradient(135deg,#134166,#1a5a8a)',
        color: '#fff',
        boxShadow: '0 4px 12px rgba(13,59,102,0.3)'
      } : {
        background: 'rgba(0,0,0,0.04)',
        color: 'rgba(0,0,0,0.3)',
        border: '1.5px solid rgba(0,0,0,0.06)'
      })
    },
    onMouseOver: e => {
      if (!item.owned && (isGem ? wallet.gems >= item.price_gems : wallet.coins >= item.sale_price)) e.currentTarget.style.background = 'linear-gradient(135deg,#1a5a8a,#1f6a9a)';
    },
    onMouseOut: e => {
      if (!item.owned && (isGem ? wallet.gems >= item.price_gems : wallet.coins >= item.sale_price)) e.currentTarget.style.background = 'linear-gradient(135deg,#134166,#1a5a8a)';
    }
  }, item.owned ? '✓ Owned' : isGem ? wallet.gems >= item.price_gems ? /*#__PURE__*/React.createElement(React.Fragment, null, "⚡ GET IT NOW ", /*#__PURE__*/React.createElement(GemIcon, {
    size: 14
  })) : /*#__PURE__*/React.createElement(React.Fragment, null, "Need ", item.price_gems - wallet.gems, " more ", /*#__PURE__*/React.createElement(GemIcon, {
    size: 14
  })) : wallet.coins >= item.sale_price ? /*#__PURE__*/React.createElement(React.Fragment, null, "⚡ GET IT NOW ", /*#__PURE__*/React.createElement(CoinIcon, {
    size: 14
  })) : /*#__PURE__*/React.createElement(React.Fragment, null, "Need ", item.sale_price - wallet.coins, " more ", /*#__PURE__*/React.createElement(CoinIcon, null))))), len > 1 && /*#__PURE__*/React.createElement("div", {
    className: "absolute bottom-3 left-1/2 -translate-x-1/2 flex gap-2"
  }, items.map((_, i) => /*#__PURE__*/React.createElement("button", {
    key: i,
    onClick: () => setCurrent(i),
    style: {
      width: i === current ? '24px' : '8px',
      height: '8px',
      borderRadius: '4px',
      border: 'none',
      cursor: 'pointer',
      transition: 'all .3s cubic-bezier(.4,0,.2,1)',
      background: i === current ? 'linear-gradient(90deg,#4a9ec4,#0d3b66)' : 'rgba(0,0,0,0.12)',
      transform: i === current ? 'scaleY(1.2)' : 'scaleY(1)'
    }
  }))));
}

// ── RAFFLE SECTION ──
function RaffleSection({
  raffle,
  wallet,
  onBuyRaffle
}) {
  const [qty, setQty] = useState(1);
  if (!raffle || !raffle.active) {
    return /*#__PURE__*/React.createElement("div", {
      className: "game-empty",
      style: {
        borderStyle: 'solid'
      }
    }, /*#__PURE__*/React.createElement("span", null, "🎟️"), /*#__PURE__*/React.createElement("p", null, "No active raffle right now. Check back soon!"));
  }
  const canBuy = wallet.coins >= raffle.ticket_price * qty;
  return /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'relative',
      overflow: 'hidden'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: '20px'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: '16px',
      flexWrap: 'wrap'
    }
  }, /*#__PURE__*/React.createElement("div", {
    className: "text-5xl animate-bounce"
  }, "🎰"), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1
    }
  }, /*#__PURE__*/React.createElement("h3", {
    className: "text-xl font-bold",
    style: {
      color: 'var(--teal-2)'
    }
  }, "🎮 ", raffle.prize_name), /*#__PURE__*/React.createElement("p", {
    style: {
      color: '#4a9ec4',
      fontSize: '.85rem'
    }
  }, raffle.prize_value || 'Win big!'))), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: '16px',
      flexWrap: 'wrap',
      alignItems: 'center'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: '16px',
      fontSize: '.85rem'
    }
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("span", {
    style: {
      color: 'rgba(42,42,58,0.5)'
    }
  }, "Sold:"), " ", /*#__PURE__*/React.createElement("span", {
    style: {
      color: '#4a9ec4',
      fontWeight: 700
    }
  }, raffle.total_tickets_sold || 0)), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("span", {
    style: {
      color: 'rgba(42,42,58,0.5)'
    }
  }, "Your Tickets:"), " ", /*#__PURE__*/React.createElement("span", {
    style: {
      color: '#4a9ec4',
      fontWeight: 700
    }
  }, raffle.user_tickets || 0)), /*#__PURE__*/React.createElement(CountdownTimer, {
    expiresAt: raffle.ends_at
  }))), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: '12px',
      flexWrap: 'wrap'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: '6px',
      background: 'rgba(0,0,0,0.04)',
      border: '1.5px solid rgba(0,0,0,0.08)',
      borderRadius: '10px',
      padding: '4px 6px'
    }
  }, /*#__PURE__*/React.createElement("button", {
    onClick: () => setQty(Math.max(1, qty - 1)),
    style: {
      width: '32px',
      height: '32px',
      borderRadius: '8px',
      border: 'none',
      background: 'rgba(74,158,196,0.15)',
      cursor: 'pointer',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontSize: '1.1rem',
      color: '#4a9ec4'
    }
  }, "−"), /*#__PURE__*/React.createElement("span", {
    style: {
      width: '32px',
      textAlign: 'center',
      fontWeight: 700,
      color: 'var(--teal-2)'
    }
  }, qty), /*#__PURE__*/React.createElement("button", {
    onClick: () => setQty(Math.min(10, qty + 1)),
    style: {
      width: '32px',
      height: '32px',
      borderRadius: '8px',
      border: 'none',
      background: 'rgba(74,158,196,0.15)',
      cursor: 'pointer',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontSize: '1.1rem',
      color: '#4a9ec4'
    }
  }, "+")), /*#__PURE__*/React.createElement("span", {
    style: {
      color: '#f59e0b',
      fontWeight: 700
    }
  }, "🎟️ ", raffle.ticket_price * qty, " ", /*#__PURE__*/React.createElement(CoinIcon, {
    size: 14
  })), /*#__PURE__*/React.createElement("button", {
    onClick: () => onBuyRaffle(raffle.id, qty),
    disabled: !canBuy,
    className: "game-btn game-btn-primary",
    style: {
      padding: '10px 28px',
      cursor: canBuy ? 'pointer' : 'not-allowed',
      ...(!canBuy ? {
        background: 'rgba(0,0,0,0.04)',
        color: 'rgba(0,0,0,0.3)',
        boxShadow: 'none'
      } : {})
    }
  }, "🎟️ Buy Tickets"))));
}

// ── BUNDLE CARD ──
function BundleCard({
  bundle,
  wallet,
  onBuy,
  index
}) {
  const isLegendBundle = bundle.name?.toLowerCase().includes('legend');
  const isGem = bundle.price_gems > 0;
  const cost = isGem ? bundle.price_gems : bundle.sale_price;
  const canAfford = isGem ? wallet.gems >= cost : wallet.coins >= cost;
  const needMore = cost - (isGem ? wallet.gems : wallet.coins);
  return /*#__PURE__*/React.createElement("div", {
    className: `shop-card card-enter ${isLegendBundle ? 'legendary shimmer-gold' : ''}`,
    style: {
      animationDelay: index * 0.08 + 's',
      cursor: 'pointer'
    }
  }, isLegendBundle && /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: '-6px',
      right: '-6px',
      background: 'linear-gradient(135deg,#f59e0b,#f97316)',
      color: '#000',
      fontSize: '.65rem',
      fontWeight: 700,
      padding: '3px 12px',
      borderRadius: '999px',
      zIndex: 10
    }
  }, "BEST VALUE 👑"), bundle.name?.includes('Starter') && /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: '-6px',
      left: '-6px',
      background: 'linear-gradient(135deg,#16a34a,#22c55e)',
      color: '#fff',
      fontSize: '.65rem',
      fontWeight: 700,
      padding: '3px 12px',
      borderRadius: '999px',
      zIndex: 10
    }
  }, "SAVE 44%"), bundle.name?.includes('Grind') && /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: '-6px',
      left: '-6px',
      background: 'linear-gradient(135deg,#134166,#1a5a8a)',
      color: '#fff',
      fontSize: '.65rem',
      fontWeight: 700,
      padding: '3px 12px',
      borderRadius: '999px',
      zIndex: 10
    }
  }, "MOST POPULAR 🔥"), /*#__PURE__*/React.createElement("div", {
    className: "text-5xl text-center mb-3"
  }, bundle.icon || '🔓'), /*#__PURE__*/React.createElement("h3", {
    className: "font-bold text-base mb-1",
    style: {
      color: 'var(--teal-2)'
    }
  }, bundle.name), /*#__PURE__*/React.createElement("p", {
    className: "text-xs mb-2",
    style: {
      color: 'rgba(42,42,58,0.5)'
    }
  }, bundle.description), /*#__PURE__*/React.createElement("div", {
    className: "space-y-1 mb-3"
  }, (bundle.includes || []).map((inc, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    className: "text-xs flex items-center gap-1",
    style: {
      color: 'rgba(42,42,58,0.5)'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      color: '#16a34a'
    }
  }, "✓"), " ", inc))), /*#__PURE__*/React.createElement("div", {
    className: "flex items-center gap-2 mb-3"
  }, bundle.original_price && /*#__PURE__*/React.createElement("div", {
    style: {
      color: 'rgba(42,42,58,0.3)',
      fontSize: '.8rem',
      textDecoration: 'line-through'
    }
  }, bundle.original_price, " ", /*#__PURE__*/React.createElement(CoinIcon, null)), isGem ? /*#__PURE__*/React.createElement("div", {
    className: "text-lg font-bold",
    style: {
      color: '#c084fc'
    }
  }, /*#__PURE__*/React.createElement(GemIcon, {
    size: 18
  }), " ", bundle.price_gems) : /*#__PURE__*/React.createElement("div", {
    className: "text-lg font-bold",
    style: {
      color: '#f59e0b'
    }
  }, /*#__PURE__*/React.createElement(CoinIcon, {
    size: 18
  }), " ", bundle.sale_price)), /*#__PURE__*/React.createElement("button", {
    onClick: () => onBuy(bundle, null, isGem ? 'gems' : 'coins'),
    className: "game-btn",
    style: {
      width: '100%',
      justifyContent: 'center',
      padding: '10px 0',
      fontSize: '.8rem',
      cursor: canAfford ? 'pointer' : 'not-allowed',
      ...(canAfford ? {
        background: 'linear-gradient(135deg,#134166,#1a5a8a)',
        color: '#fff',
        boxShadow: '0 4px 12px rgba(13,59,102,0.3)'
      } : {
        background: 'rgba(0,0,0,0.04)',
        color: 'rgba(0,0,0,0.3)',
        border: '1.5px solid rgba(0,0,0,0.06)'
      })
    },
    onMouseOver: e => {
      if (canAfford) e.currentTarget.style.background = 'linear-gradient(135deg,#1a5a8a,#1f6a9a)';
    },
    onMouseOut: e => {
      if (canAfford) e.currentTarget.style.background = 'linear-gradient(135deg,#134166,#1a5a8a)';
    }
  }, canAfford ? /*#__PURE__*/React.createElement(React.Fragment, null, "Buy ", isGem ? /*#__PURE__*/React.createElement(GemIcon, {
    size: 14
  }) : /*#__PURE__*/React.createElement(CoinIcon, {
    size: 14
  }), " ", cost) : /*#__PURE__*/React.createElement(React.Fragment, null, "Need ", needMore, " more ", isGem ? /*#__PURE__*/React.createElement(GemIcon, {
    size: 14
  }) : /*#__PURE__*/React.createElement(CoinIcon, null))));
}

// ── CRATE OPEN MODAL ──
function CrateOpenModal({
  item,
  reward,
  onClose
}) {
  const [phase, setPhase] = useState('loading');
  const particlesRef = useRef(null);
  useEffect(() => {
    if (!item) return;
    setPhase('loading');
    setCrateParticles(particlesRef.current);
  }, [item]);
  useEffect(() => {
    if (reward) {
      setPhase('reveal');
      burstConfetti();
      setTimeout(() => burstConfetti(), 400);
      setTimeout(() => burstConfetti(), 800);
      setTimeout(() => burstConfetti(), 1200);
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
  }, /*#__PURE__*/React.createElement("canvas", {
    ref: particlesRef,
    className: "absolute inset-0 pointer-events-none z-0"
  }), /*#__PURE__*/React.createElement("div", {
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
      background: 'radial-gradient(circle, rgba(13,59,102,0.3) 0%, transparent 70%)',
      animation: 'cratePulse 1s ease-in-out infinite'
    }
  }))), /*#__PURE__*/React.createElement("div", {
    className: "flex gap-2"
  }, [0, 1, 2, 3, 4, 5].map(i => /*#__PURE__*/React.createElement("div", {
    key: i,
    className: "w-2.5 h-2.5 rounded-full",
    style: {
      background: `hsl(${200 + i * 12}, 70%, 50%)`,
      animation: `crateDot2 0.6s ease-in-out ${i * 0.12}s infinite alternate`
    }
  }))), /*#__PURE__*/React.createElement("p", {
    className: "text-gray-400 text-sm tracking-[6px] uppercase font-bold animate-pulse"
  }, "Unlocking...")), phase === 'reveal' && reward && /*#__PURE__*/React.createElement("div", {
    className: "flex flex-col items-center gap-5",
    style: {
      animation: 'crateReveal2 0.7s cubic-bezier(0.16, 1, 0.3, 1) both'
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
        @keyframes crateShake3 {
          0% { transform: translateX(-12px) rotate(-8deg) scale(1.03); }
          100% { transform: translateX(12px) rotate(8deg) scale(0.97); }
        }
        @keyframes cratePulse {
          0%, 100% { transform: scale(0.8); opacity: 0.3; }
          50% { transform: scale(1.5); opacity: 0.6; }
        }
        @keyframes crateDot2 {
          0% { opacity: 0.2; transform: scale(0.7) translateY(0); }
          100% { opacity: 1; transform: scale(1.3) translateY(-8px); }
        }
        @keyframes crateReveal2 {
          0% { opacity: 0; transform: scale(0.2) rotateY(120deg); filter: blur(10px); }
          60% { filter: blur(2px); }
          100% { opacity: 1; transform: scale(1) rotateY(0deg); filter: blur(0); }
        }
        @keyframes crateBurst {
          0%, 100% { transform: translate(-50%, -50%) scale(1); opacity: 0.4; }
          50% { transform: translate(-50%, -50%) scale(1.8); opacity: 0.1; }
        }
        @keyframes crateFloat {
          0%, 100% { transform: translateY(0px); }
          50% { transform: translateY(-8px); }
        }
        @keyframes crateShine {
          0% { transform: skewX(-20deg) translateX(-100%); }
          100% { transform: skewX(-20deg) translateX(200%); }
        }
      `));
}
function setCrateParticles(canvas) {
  if (!canvas || !canvas.getContext) return;
  const ctx = canvas.getContext('2d');
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
  const particles = Array.from({
    length: 40
  }, () => ({
    x: Math.random() * canvas.width,
    y: Math.random() * canvas.height,
    vx: (Math.random() - 0.5) * 3,
    vy: (Math.random() - 0.5) * 3 - 1,
    size: Math.random() * 4 + 1,
    alpha: Math.random() * 0.5 + 0.2,
    hue: Math.random() * 60 + 240
  }));
  let running = true;
  function draw() {
    if (!running) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    particles.forEach(p => {
      p.x += p.vx;
      p.y += p.vy;
      if (p.x < 0 || p.x > canvas.width) p.vx *= -1;
      if (p.y < 0 || p.y > canvas.height) {
        p.y = canvas.height;
        p.vy = -Math.abs(p.vy);
      }
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
      ctx.fillStyle = `hsla(${p.hue}, 80%, 60%, ${p.alpha})`;
      ctx.fill();
    });
    requestAnimationFrame(draw);
  }
  draw();
  setTimeout(() => {
    running = false;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
  }, 3000);
}

// ── MAIN APP ──
function ShopApp() {
  const [items, setItems] = useState([]);
  const [featured, setFeatured] = useState([]);
  const [wallet, setWallet] = useState({
    coins: 1250,
    gems: 45
  });
  const [inventory, setInventory] = useState([]);
  const [raffle, setRaffle] = useState(null);
  const [recent, setRecent] = useState([]);
  const [activeSection, setActiveSection] = useState('featured');
  const [openingCrate, setOpeningCrate] = useState(null);
  const [crateReward, setCrateReward] = useState(null);
  const [loading, setLoading] = useState(false);
  const [dailyFree, setDailyFree] = useState({
    available: true,
    nextIn: 0
  });
  const walletRef = useRef(null);
  const fetchData = useCallback(async () => {
    try {
      const [itemsRes, featuredRes, walletRes, invRes, raffleRes, recentRes] = await Promise.all([fetch(API.items).then(r => r.json()), fetch(API.featured).then(r => r.json()), fetch(API.wallet).then(r => r.json()), fetch(API.inventory).then(r => r.json()), fetch(API.raffle).then(r => r.json()), fetch(API.recent).then(r => r.json())]);
      setItems(itemsRes);
      setFeatured(featuredRes);
      setWallet(walletRes);
      setInventory(invRes);
      setRaffle(raffleRes);
      setRecent(recentRes);
    } catch (e) {
      console.error('Fetch error, using fallback data', e);
      loadFallbackData();
    } finally {
      setLoading(false);
    }
  }, []);
  const loadFallbackData = () => {
    const fallbackItems = [{
      id: 1,
      name: 'XP Surge',
      description: '2x XP for 24 hours',
      category: 'hot',
      rarity: 'epic',
      price_coins: 800,
      sale_price: 500,
      discount_percent: 38,
      icon: '⚡',
      is_limited: false,
      stock_remaining: -1,
      owned: false,
      price_gems: 0
    }, {
      id: 2,
      name: 'Streak Shield',
      description: 'Protect your streak for 1 missed day',
      category: 'hot',
      rarity: 'rare',
      price_coins: 300,
      sale_price: 300,
      discount_percent: 0,
      icon: '🛡️',
      is_limited: false,
      stock_remaining: -1,
      owned: false,
      price_gems: 0
    }, {
      id: 3,
      name: 'Challenge Skip',
      description: 'Skip any challenge',
      category: 'hot',
      rarity: 'common',
      price_coins: 150,
      sale_price: 150,
      discount_percent: 0,
      icon: '🎯',
      is_limited: false,
      stock_remaining: -1,
      owned: false,
      price_gems: 0
    }, {
      id: 4,
      name: 'Hint Token x3',
      description: 'Reveal hints on hard challenges',
      category: 'hot',
      rarity: 'common',
      price_coins: 200,
      sale_price: 200,
      discount_percent: 0,
      icon: '💡',
      is_limited: false,
      stock_remaining: -1,
      owned: false,
      price_gems: 0
    }, {
      id: 5,
      name: 'XP Boost 2x / 24hr',
      description: 'Double XP for 24 hours',
      category: 'boosts',
      rarity: 'rare',
      price_coins: 500,
      sale_price: 500,
      discount_percent: 0,
      icon: '⚡',
      is_limited: false,
      stock_remaining: -1,
      owned: false,
      price_gems: 0
    }, {
      id: 6,
      name: 'XP Boost 2x / 72hr',
      description: 'Double XP for 3 days',
      category: 'boosts',
      rarity: 'epic',
      price_coins: 1200,
      sale_price: 1200,
      discount_percent: 0,
      icon: '⚡',
      is_limited: false,
      stock_remaining: -1,
      owned: false,
      price_gems: 0
    }, {
      id: 7,
      name: 'Money Multiplier 1.5x',
      description: '1.5x money for 24 hours',
      category: 'boosts',
      rarity: 'rare',
      price_coins: 400,
      sale_price: 400,
      discount_percent: 0,
      icon: '🔥',
      is_limited: false,
      stock_remaining: -1,
      owned: false,
      price_gems: 0
    }, {
      id: 8,
      name: 'Weekend Warrior Pass',
      description: '2x money all weekend',
      category: 'boosts',
      rarity: 'epic',
      price_coins: 600,
      sale_price: 600,
      discount_percent: 0,
      icon: '📅',
      is_limited: false,
      stock_remaining: -1,
      owned: false,
      price_gems: 0
    }, {
      id: 9,
      name: 'Challenge Reroll x3',
      description: 'Reroll 3 challenges',
      category: 'boosts',
      rarity: 'common',
      price_coins: 250,
      sale_price: 250,
      discount_percent: 0,
      icon: '🔄',
      is_limited: false,
      stock_remaining: -1,
      owned: false,
      price_gems: 0
    }, {
      id: 10,
      name: 'Mega Shield (3 days)',
      description: '3-day streak protection',
      category: 'boosts',
      rarity: 'rare',
      price_coins: 750,
      sale_price: 750,
      discount_percent: 0,
      icon: '🛡️',
      is_limited: false,
      stock_remaining: -1,
      owned: false,
      price_gems: 0
    }, {
      id: 16,
      name: 'Flame Profile Border',
      description: 'Animated flame border',
      category: 'flex',
      rarity: 'epic',
      price_coins: 0,
      sale_price: 0,
      discount_percent: 0,
      icon: '🔥',
      is_limited: false,
      stock_remaining: -1,
      owned: false,
      price_gems: 25
    }, {
      id: 17,
      name: 'Electric Border',
      description: 'Animated electric border',
      category: 'flex',
      rarity: 'epic',
      price_coins: 0,
      sale_price: 0,
      discount_percent: 0,
      icon: '⚡',
      is_limited: false,
      stock_remaining: -1,
      owned: false,
      price_gems: 25
    }, {
      id: 18,
      name: 'Shooting Star Effect',
      description: 'Shooting star profile effect',
      category: 'flex',
      rarity: 'legendary',
      price_coins: 0,
      sale_price: 0,
      discount_percent: 0,
      icon: '🌟',
      is_limited: false,
      stock_remaining: -1,
      owned: false,
      price_gems: 50
    }, {
      id: 21,
      name: 'Basic Crate',
      description: '1 random Common or Rare item',
      category: 'lootbox',
      rarity: 'common',
      price_coins: 300,
      sale_price: 300,
      discount_percent: 0,
      icon: '📦',
      is_limited: false,
      stock_remaining: -1,
      owned: false,
      price_gems: 0
    }, {
      id: 22,
      name: 'Epic Crate',
      description: '1 Rare guaranteed, Epic chance',
      category: 'lootbox',
      rarity: 'epic',
      price_coins: 0,
      sale_price: 0,
      discount_percent: 0,
      icon: '📦',
      is_limited: false,
      stock_remaining: -1,
      owned: false,
      price_gems: 12
    }, {
      id: 23,
      name: 'Legendary Crate',
      description: '1 Epic guaranteed, Legendary chance',
      category: 'lootbox',
      rarity: 'legendary',
      price_coins: 0,
      sale_price: 0,
      discount_percent: 0,
      icon: '📦',
      is_limited: false,
      stock_remaining: -1,
      owned: false,
      price_gems: 30
    }, {
      id: 24,
      name: 'Mystery Box',
      description: 'Could be anything...',
      category: 'lootbox',
      rarity: 'legendary',
      price_coins: 500,
      sale_price: 500,
      discount_percent: 0,
      icon: '🎁',
      is_limited: false,
      stock_remaining: -1,
      owned: false,
      price_gems: 0
    }];
    const fallbackFeatured = [{
      id: 1,
      name: 'XP Surge',
      description: '2x XP for 24 hours - Limited Time Sale!',
      category: 'hot',
      rarity: 'epic',
      price_coins: 800,
      sale_price: 500,
      discount_percent: 38,
      icon: '⚡',
      is_limited: false,
      stock_remaining: -1,
      owned: false,
      price_gems: 0,
      expires_at: new Date(Date.now() + 86400000).toISOString()
    }, {
      id: 2,
      name: 'Legendary Crate',
      description: 'Guaranteed Epic with Legendary chance!',
      category: 'lootbox',
      rarity: 'legendary',
      price_coins: 0,
      sale_price: 0,
      discount_percent: 0,
      icon: '📦',
      is_limited: false,
      stock_remaining: -1,
      owned: false,
      price_gems: 30
    }];
    setItems(fallbackItems);
    setFeatured(fallbackFeatured);
    setRecent([{
      item: 'XP Surge',
      icon: '⚡',
      coins_spent: 500,
      purchased_at: new Date().toISOString()
    }]);
  };
  useEffect(() => {
    fetchData();
  }, [fetchData]);
  const handleOpenCrate = async (item, cardEl) => {
    if (!item.owned) return;
    setOpeningCrate(item);
    setCrateReward(null);
    try {
      const invItem = inventory.find(i => i.item_id === item.id);
      const res = await fetch('/api/shop/crate/open/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCSRF()
        },
        body: JSON.stringify({
          inventory_id: invItem ? invItem.id : null,
          item_id: item.id
        })
      });
      let data;
      try {
        data = await res.json();
      } catch (_) {
        showToast('❌ Server error. Try again.');
        setOpeningCrate(null);
        return;
      }
      if (!res.ok) {
        showToast('❌ ' + (data.error || 'Failed'));
        setOpeningCrate(null);
        return;
      }
      setCrateReward(data.item);
      setItems(prev => prev.map(i => i.id === item.id ? {
        ...i,
        owned: false
      } : i));
      if (invItem) setInventory(prev => prev.filter(i => i.id !== invItem.id));
      burstConfetti();
      setTimeout(() => burstConfetti(), 500);
    } catch (e) {
      console.error('Crate open error:', e);
      showToast('❌ Network error. Check your connection.');
      setOpeningCrate(null);
    }
  };
  const handleBuy = async (item, cardEl, currency = 'coins') => {
    const cost = currency === 'gems' ? item.price_gems : item.sale_price;
    if (item.owned || (currency === 'gems' ? wallet.gems < cost : wallet.coins < cost)) return;
    try {
      const res = await fetch(API.buy, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCSRF()
        },
        body: JSON.stringify({
          item_id: item.id,
          currency
        })
      });
      if (!res.ok) {
        const err = await res.json();
        showToast('❌ ' + (err.item_id?.[0] || err.non_field_errors?.[0] || 'Purchase failed'));
        return;
      }
      const data = await res.json();
      if (cardEl) coinFly(cardEl, walletRef.current);
      burstConfetti();
      if (currency === 'gems') {
        setWallet(p => ({
          ...p,
          gems: data.gems_left
        }));
      } else {
        setWallet(p => ({
          ...p,
          coins: data.coins_left
        }));
      }
      if (item.category === 'lootbox' || item.name === 'AI Profile Pic Generator') {
        const invRes = await fetch(API.inventory).then(r => r.json());
        setInventory(invRes);
      } else {
        setInventory(p => [...p, {
          item_id: item.id,
          name: item.name
        }]);
      }
      if (item.category === 'lootbox') {
        showToast(`📦 ${item.name} purchased! Open it from the shop or inventory!`);
      } else if (item.name === 'AI Profile Pic Generator') {
        showToast(`🤖 +3 AI Profile generations! Use them in Inventory!`);
      } else {
        showToast(`🔥 ${item.name} activated!`);
      }
      setItems(prev => prev.map(i => i.id === item.id ? {
        ...i,
        owned: true
      } : i));
      setFeatured(prev => prev.map(i => i.id === item.id ? {
        ...i,
        owned: true
      } : i));
    } catch (e) {
      showToast('❌ Network error. Try again.');
    }
  };
  const handleBuyRaffle = async (raffleId, qty) => {
    try {
      const res = await fetch(API.raffleBuy, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCSRF()
        },
        body: JSON.stringify({
          raffle_id: raffleId,
          quantity: qty
        })
      });
      if (!res.ok) {
        const err = await res.json();
        showToast('❌ ' + (err.quantity?.[0] || err.non_field_errors?.[0] || 'Failed'));
        return;
      }
      const data = await res.json();
      setWallet(p => ({
        ...p,
        coins: data.coins_left
      }));
      showToast(`🎟️ ${qty} ticket${qty > 1 ? 's' : ''} purchased! Good luck!`);
      fetchData();
    } catch (e) {
      showToast('❌ Network error.');
    }
  };
  const handleCustomTitle = async () => {
    const input = document.getElementById('customTitleInput');
    const result = document.getElementById('customTitleResult');
    const title = input ? input.value.trim() : '';
    if (!title) {
      showToast('✏️ Enter a title first!');
      if (result) {
        result.style.display = 'block';
        result.className = 'text-xs mt-2 font-semibold text-red-400';
        result.textContent = 'Enter a title!';
      }
      return;
    }
    if (title.length > 30) {
      showToast('✏️ Max 30 characters!');
      return;
    }
    try {
      const res = await fetch('/api/shop/custom-title/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCSRF()
        },
        body: JSON.stringify({
          title
        })
      });
      const data = await res.json();
      if (data.success) {
        setWallet(p => ({
          ...p,
          coins: data.coins_left
        }));
        window.USER.title = data.title;
        window.USER.flex_effect = 'title';
        showToast(`✨ "${data.title}" activated!`);
        if (result) {
          result.style.display = 'block';
          result.className = 'text-xs mt-2 font-semibold text-green-400';
          result.textContent = data.message;
        }
        if (input) input.value = '';
      } else {
        showToast('❌ ' + (data.error || 'Failed'));
        if (result) {
          result.style.display = 'block';
          result.className = 'text-xs mt-2 font-semibold text-red-400';
          result.textContent = data.error;
        }
      }
    } catch (e) {
      showToast('❌ Network error.');
    }
  };
  const getCSRF = () => {
    const m = document.cookie.match(/csrftoken=([^;]+)/);
    return m ? m[1] : '';
  };
  const getItemSection = item => {
    const s = item.name;
    if (['Flame Profile Border', 'Electric Border', 'Ice Border'].some(n => s.includes(n))) return 'border-animations';
    if (['Shooting Star Effect', 'Crystal Aura', 'Frostwind', 'Thunder Storm', 'Fire Spirit', 'Mystic Mist', 'Stardust Burst', 'Ember Sparks', 'Snowfall', 'Energy Arc', 'Neon Rain', 'Spirit Orbs', 'Sakura Storm', 'Ocean Depths', 'Sunset Horizon', 'Cosmic Nebula', 'Neon Grid', 'Starry Sky', 'Lava Flow'].some(n => s.includes(n))) return 'particles';
    if (s.includes('Boost') || s.includes('Shield') || s.includes('Skip') || s.includes('Token') || s.includes('Multiplier') || s.includes('Pass') || s.includes('Reroll') || s.includes('Surge')) return 'boosts';
    if (s.includes('Crate') || s.includes('Mystery Box')) return 'crates';
    return null;
  };
  const sectionItems = items.filter(i => getItemSection(i) === activeSection);
  const bundles = useMemo(() => [{
    id: 'b1',
    name: 'Starter Bundle',
    icon: '🚀',
    description: 'Everything you need to start',
    original_price: 1800,
    sale_price: 1000,
    price_gems: 15,
    includes: ['Streak Shield', 'Challenge Skip x2', 'Hint Token x3']
  }, {
    id: 'b2',
    name: 'Grind Bundle',
    icon: '👑',
    description: 'For the serious grinder',
    original_price: 5500,
    sale_price: 3500,
    price_gems: 40,
    includes: ['XP Boost 72hr', 'Coin Multiplier 24hr', '"Grinder" Title', 'Epic Crate']
  }, {
    id: 'b3',
    name: 'Legend Bundle',
    icon: '🌟',
    description: 'The ultimate package',
    original_price: 0,
    sale_price: 0,
    price_gems: 80,
    includes: ['XP Boost 72hr x2', 'Animated Border', 'Legendary Title', 'Legendary Crate', 'Leaderboard Pin']
  }], []);
  return /*#__PURE__*/React.createElement("div", {
    className: "min-h-screen relative z-10",
    style: {
      paddingTop: '126px'
    }
  }, /*#__PURE__*/React.createElement("header", {
    className: "shop-topbar"
  }, /*#__PURE__*/React.createElement("a", {
    href: "/dashboard/",
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: '8px',
      textDecoration: 'none'
    }
  }, /*#__PURE__*/React.createElement("img", {
    src: "/static/LOGO.png",
    alt: "ChillX",
    style: {
      height: '100px',
      width: 'auto',
      filter: 'drop-shadow(0 0 20px rgba(74,158,196,0.5))'
    }
  })), /*#__PURE__*/React.createElement("div", {
    ref: walletRef
  }, /*#__PURE__*/React.createElement(WalletBar, {
    wallet: wallet
  }))), /*#__PURE__*/React.createElement("nav", {
    className: "shop-sidebar"
  }, [{
    key: 'featured',
    icon: 'fa-bolt',
    label: 'FEAT.',
    color: 'blue'
  }, {
    key: 'boosts',
    icon: 'fa-arrow-up',
    label: 'BOOST',
    color: 'blue'
  }, {
    key: 'border-animations',
    icon: 'fa-border-all',
    label: 'BORDER',
    color: 'gold'
  }, {
    key: 'particles',
    icon: 'fa-wand-magic-sparkles',
    label: 'PART.',
    color: 'purple'
  }, {
    key: 'crates',
    icon: 'fa-box',
    label: 'CRATE',
    color: 'gold'
  }, {
    key: 'bundles',
    icon: 'fa-box-open',
    label: 'BUNDLE',
    color: 'purple'
  }, {
    key: 'raffle',
    icon: 'fa-ticket',
    label: 'RAFFLE',
    color: 'gold'
  }, {
    key: 'freebies',
    icon: 'fa-gift',
    label: 'FREE',
    color: 'green'
  }, {
    key: 'custom',
    icon: 'fa-pen',
    label: 'TITLE',
    color: 'pink'
  }].map(tab => /*#__PURE__*/React.createElement("button", {
    key: tab.key,
    className: 'shop-tab' + (activeSection === tab.key ? ' active' : ''),
    "data-color": tab.color,
    onClick: () => setActiveSection(tab.key)
  }, /*#__PURE__*/React.createElement("i", {
    className: `fas ${tab.icon}`
  }), /*#__PURE__*/React.createElement("span", null, tab.label)))), /*#__PURE__*/React.createElement("main", {
    className: "max-w-7xl mx-auto px-4 pt-2 pb-20",
    style: {
      marginLeft: '110px'
    }
  }, activeSection === 'featured' && /*#__PURE__*/React.createElement("div", {
    className: "space-y-6 tab-content",
    key: "featured"
  }, featured.length > 0 && /*#__PURE__*/React.createElement("div", {
    className: "sr"
  }, /*#__PURE__*/React.createElement(FeaturedCarousel, {
    items: featured,
    wallet: wallet,
    onBuy: handleBuy,
    onOpenCrate: handleOpenCrate
  })), recent.length > 0 && /*#__PURE__*/React.createElement("div", {
    className: "shop-section sr sr-up"
  }, /*#__PURE__*/React.createElement("div", {
    className: "game-section-header"
  }, "🕐 Recent Purchases"), /*#__PURE__*/React.createElement("div", {
    className: "flex gap-3 overflow-x-auto pb-2"
  }, recent.map((r, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    className: "shrink-0",
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: '12px',
      padding: '14px 20px',
      minWidth: '200px',
      background: '#fff',
      borderRadius: '14px',
      border: '1.5px solid rgba(0,0,0,0.06)',
      boxShadow: '0 2px 8px rgba(0,0,0,0.04)',
      transition: 'all .2s ease',
      cursor: 'pointer'
    },
    onMouseOver: e => {
      e.currentTarget.style.borderColor = 'var(--teal-1)';
      e.currentTarget.style.boxShadow = '0 4px 12px rgba(13,59,102,0.1)';
      e.currentTarget.style.transform = 'translateY(-2px)';
    },
    onMouseOut: e => {
      e.currentTarget.style.borderColor = 'rgba(0,0,0,0.06)';
      e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.04)';
      e.currentTarget.style.transform = 'translateY(0)';
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: '1.8rem'
    }
  }, r.icon || '🎁'), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    className: "text-sm font-semibold",
    style: {
      color: 'var(--teal-2)'
    }
  }, r.item), /*#__PURE__*/React.createElement("div", {
    className: "text-xs",
    style: {
      color: '#4a9ec4'
    }
  }, /*#__PURE__*/React.createElement(CoinIcon, null), " Rs ", r.coins_spent))))))), activeSection === 'boosts' && /*#__PURE__*/React.createElement("div", {
    className: "tab-content",
    key: "boosts"
  }, /*#__PURE__*/React.createElement("div", {
    className: "shop-section sr"
  }, /*#__PURE__*/React.createElement("div", {
    className: "game-section-header"
  }, "⚡ Boosts"), /*#__PURE__*/React.createElement("div", {
    className: "grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 stagger-children"
  }, sectionItems.length > 0 ? sectionItems.map((item, i) => /*#__PURE__*/React.createElement(ItemCard, {
    key: item.id,
    item: item,
    wallet: wallet,
    onBuy: handleBuy,
    onOpenCrate: handleOpenCrate,
    index: i
  })) : /*#__PURE__*/React.createElement("div", {
    className: "game-empty"
  }, /*#__PURE__*/React.createElement("span", null, "⚡"), /*#__PURE__*/React.createElement("p", null, "No boosts available!"))))), activeSection === 'border-animations' && /*#__PURE__*/React.createElement("div", {
    className: "tab-content",
    key: "borders"
  }, /*#__PURE__*/React.createElement("div", {
    className: "shop-section sr"
  }, /*#__PURE__*/React.createElement("div", {
    className: "game-section-header"
  }, "🔥 Border Animations"), /*#__PURE__*/React.createElement("div", {
    className: "grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 stagger-children"
  }, sectionItems.length > 0 ? sectionItems.map((item, i) => /*#__PURE__*/React.createElement(ItemCard, {
    key: item.id,
    item: item,
    wallet: wallet,
    onBuy: handleBuy,
    onOpenCrate: handleOpenCrate,
    index: i
  })) : /*#__PURE__*/React.createElement("div", {
    className: "game-empty"
  }, /*#__PURE__*/React.createElement("span", null, "🔥"), /*#__PURE__*/React.createElement("p", null, "No border animations available!"))))), activeSection === 'particles' && /*#__PURE__*/React.createElement("div", {
    className: "tab-content",
    key: "particles"
  }, /*#__PURE__*/React.createElement("div", {
    className: "shop-section sr"
  }, /*#__PURE__*/React.createElement("div", {
    className: "game-section-header"
  }, "✨ Particles"), /*#__PURE__*/React.createElement("div", {
    className: "grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 stagger-children"
  }, sectionItems.length > 0 ? sectionItems.map((item, i) => /*#__PURE__*/React.createElement(ItemCard, {
    key: item.id,
    item: item,
    wallet: wallet,
    onBuy: handleBuy,
    onOpenCrate: handleOpenCrate,
    index: i
  })) : /*#__PURE__*/React.createElement("div", {
    className: "game-empty"
  }, /*#__PURE__*/React.createElement("span", null, "✨"), /*#__PURE__*/React.createElement("p", null, "No particle effects available!"))))), activeSection === 'crates' && /*#__PURE__*/React.createElement("div", {
    className: "tab-content",
    key: "crates"
  }, /*#__PURE__*/React.createElement("div", {
    className: "shop-section sr",
    style: {
      borderColor: 'rgba(245,158,11,0.2)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    className: "game-section-header",
    style: {
      color: '#f59e0b'
    }
  }, "📦 Crates"), /*#__PURE__*/React.createElement("div", {
    className: "grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 stagger-children"
  }, sectionItems.length > 0 ? sectionItems.map((item, i) => /*#__PURE__*/React.createElement(ItemCard, {
    key: item.id,
    item: item,
    wallet: wallet,
    onBuy: handleBuy,
    onOpenCrate: handleOpenCrate,
    index: i
  })) : /*#__PURE__*/React.createElement("div", {
    className: "game-empty"
  }, /*#__PURE__*/React.createElement("span", null, "📦"), /*#__PURE__*/React.createElement("p", null, "No crates available!"))))), activeSection === 'bundles' && /*#__PURE__*/React.createElement("div", {
    className: "shop-section tab-content",
    key: "bundles"
  }, /*#__PURE__*/React.createElement("div", {
    className: "game-section-header"
  }, "🔓 Value Bundles ", /*#__PURE__*/React.createElement("span", {
    className: "text-xs",
    style: {
      color: '#f59e0b',
      fontFamily: 'Poppins,sans-serif',
      fontWeight: 700,
      letterSpacing: '0.5px'
    }
  }, "BEST VALUE")), /*#__PURE__*/React.createElement("div", {
    className: "grid grid-cols-1 md:grid-cols-3 gap-5 stagger-children"
  }, bundles.map((b, i) => /*#__PURE__*/React.createElement("div", {
    key: b.id,
    className: "sr sr-scale"
  }, /*#__PURE__*/React.createElement(BundleCard, {
    bundle: b,
    wallet: wallet,
    onBuy: (bundle, cardEl, currency) => {
      const cost = currency === 'gems' ? bundle.price_gems : bundle.sale_price;
      if (currency === 'gems' ? wallet.gems >= cost : wallet.coins >= cost) {
        setWallet(p => ({
          ...p,
          [currency === 'gems' ? 'gems' : 'coins']: p[currency === 'gems' ? 'gems' : 'coins'] - cost
        }));
        burstConfetti();
        showToast(`🔥 ${bundle.name} purchased!`);
      }
    },
    index: i
  }))))), activeSection === 'raffle' && /*#__PURE__*/React.createElement("div", {
    className: "shop-section tab-content",
    key: "raffle"
  }, /*#__PURE__*/React.createElement("div", {
    className: "game-section-header"
  }, "🎰 Raffle"), /*#__PURE__*/React.createElement(RaffleSection, {
    raffle: raffle,
    wallet: wallet,
    onBuyRaffle: handleBuyRaffle
  })), activeSection === 'freebies' && /*#__PURE__*/React.createElement("div", {
    className: "space-y-5 tab-content",
    key: "freebies"
  }, /*#__PURE__*/React.createElement("div", {
    className: "shop-section sr sr-up"
  }, /*#__PURE__*/React.createElement("div", {
    className: "game-section-header"
  }, "🎁 Daily Free Item"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      flexWrap: 'wrap',
      gap: '16px'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: '14px'
    }
  }, /*#__PURE__*/React.createElement("span", {
    className: "text-5xl float"
  }, "🎁"), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    className: "font-bold text-lg",
    style: {
      color: 'var(--teal-2)'
    }
  }, "Free Item Every 24h"), /*#__PURE__*/React.createElement("div", {
    style: {
      color: '#4a9ec4',
      fontSize: '.85rem',
      fontWeight: 500
    }
  }, "Claim a free Common item — resets daily!"))), dailyFree.available ? /*#__PURE__*/React.createElement("button", {
    className: "game-btn game-btn-green",
    style: {
      padding: '12px 32px',
      fontSize: '1rem'
    }
  }, "CLAIM FREE 🆓") : /*#__PURE__*/React.createElement("div", {
    style: {
      color: 'rgba(42,42,58,0.5)',
      fontSize: '.9rem'
    }
  }, "Next free in: ", /*#__PURE__*/React.createElement("span", {
    style: {
      color: '#16a34a',
      fontWeight: 700
    }
  }, dailyFree.nextIn, "h"))))), activeSection === 'custom' && /*#__PURE__*/React.createElement("div", {
    className: "shop-section tab-content",
    key: "custom",
    style: {
      borderColor: 'rgba(245,158,11,0.2)',
      maxWidth: '600px',
      margin: '0 auto'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      textAlign: 'center',
      marginBottom: '20px'
    }
  }, /*#__PURE__*/React.createElement("span", {
    className: "text-6xl block mb-4"
  }, "✏️"), /*#__PURE__*/React.createElement("div", {
    className: "game-section-header",
    style: {
      justifyContent: 'center',
      border: 'none',
      color: '#f59e0b',
      fontSize: '1.4rem'
    }
  }, "Custom Title Creator"), /*#__PURE__*/React.createElement("p", {
    style: {
      color: 'rgba(42,42,58,0.5)',
      fontSize: '.9rem'
    }
  }, "Create your own unique title for Rs 2,000")), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: '12px',
      flexWrap: 'wrap',
      justifyContent: 'center'
    }
  }, /*#__PURE__*/React.createElement("input", {
    id: "customTitleInput",
    style: {
      flex: 1,
      minWidth: '220px',
      padding: '14px 18px',
      borderRadius: '12px',
      border: '1.5px solid rgba(245,158,11,0.3)',
      background: '#fff',
      color: 'var(--ink)',
      fontSize: '1rem',
      fontWeight: 600,
      outline: 'none',
      fontFamily: 'Poppins,sans-serif',
      textAlign: 'center',
      boxShadow: '0 2px 8px rgba(0,0,0,0.04)'
    },
    placeholder: "Your unique title...",
    maxLength: "30",
    onKeyDown: e => {
      if (e.key === 'Enter') handleCustomTitle();
    }
  }), /*#__PURE__*/React.createElement("button", {
    className: "game-btn game-btn-gold",
    onClick: handleCustomTitle,
    style: {
      padding: '14px 32px'
    }
  }, "✨ CREATE TITLE")), /*#__PURE__*/React.createElement("div", {
    id: "customTitleResult",
    className: "text-xs mt-3 font-semibold text-center",
    style: {
      display: 'none',
      color: '#22c55e'
    }
  }))), openingCrate && /*#__PURE__*/React.createElement(CrateOpenModal, {
    item: openingCrate,
    reward: crateReward,
    onClose: () => {
      setOpeningCrate(null);
      setCrateReward(null);
      fetchData();
    }
  }));
}

// ── RENDER ──
const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(/*#__PURE__*/React.createElement(ShopApp, null));