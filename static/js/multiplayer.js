console.log('multiplayer: babel script executing');
const {
  useState,
  useEffect,
  useRef,
  useCallback
} = React;
const {
  createRoot
} = ReactDOM;

// ── HOOK: useMultiplayerSocket ──
function useMultiplayerSocket(roomCode, userId, onMessage) {
  const wsRef = useRef(null);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [roomState, setRoomState] = useState(null);
  const userIdRef = useRef(userId);
  userIdRef.current = userId;
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;
  const sendProgress = useCallback(payload => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'progress_update',
        progress: payload
      }));
    }
  }, []);
  const sendReady = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'ready',
        ready: true
      }));
    }
  }, []);
  const sendChallengeComplete = useCallback(result => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'challenge_complete',
        result: result,
        completion_time: Date.now() / 1000
      }));
    }
  }, []);
  useEffect(() => {
    if (!roomCode) return;
    let reconnectTimer = null;
    let mounted = true;
    function connect() {
      if (!mounted) return;
      const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const url = `${proto}//${window.location.host}/ws/multiplayer/${roomCode}/`;
      const ws = new WebSocket(url);
      wsRef.current = ws;
      ws.onopen = () => {
        if (mounted) setConnectionStatus('connected');
      };
      ws.onmessage = e => {
        if (!mounted) return;
        try {
          const data = JSON.parse(e.data);
          if (data.type === 'player_update') {
            setRoomState(data);
          }
          if (onMessageRef.current) onMessageRef.current(data);
        } catch (err) {}
      };
      ws.onclose = () => {
        wsRef.current = null;
        if (mounted) {
          setConnectionStatus('disconnected');
          reconnectTimer = setTimeout(connect, 2000);
        }
      };
      ws.onerror = () => {
        ws.close();
      };
    }
    connect();
    return () => {
      mounted = false;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [roomCode]);
  const sendSettings = useCallback(settings => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'update_settings',
        settings: settings
      }));
    }
  }, []);
  const sendRaw = useCallback(data => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);
  return {
    sendProgress,
    sendReady,
    sendChallengeComplete,
    sendSettings,
    sendRaw,
    connectionStatus,
    roomState
  };
}

// ── COMPONENT: PlayerTracker ──
function PlayerTracker({
  player,
  challengeType,
  progress,
  isConnected
}) {
  if (!player) return null;
  var p = progress || {};
  var sc = p.score || p.current_score || 0;
  var tg = p.target || p.target_score || p.total_questions || p.total_words || 1;
  var getProgressPercent = function () {
    if (!progress) return 0;
    if (challengeType === 'typing') return (p.word_index || 0) / (p.total_words || 1) * 100;
    if (challengeType === 'quiz') return sc / tg * 100;
    if (challengeType === 'cps') return sc / (p.target_score || 80) * 100;
    if (challengeType === 'aim3d') return sc / tg * 100;
    if (challengeType === 'reaction') return (p.attempts_done || 0) / (p.total_attempts || 5) * 100;
    if (challengeType === 'memory') return (p.current_level || 0) / (p.target_level || 8) * 100;
    if (challengeType === 'runner') return sc / tg * 100;
    if (challengeType === 'tictactoe') return (p.wins || 0) / (p.target_wins || 1) * 100;
    return p.percent_complete || 0;
  };
  var getProgressText = function () {
    if (!progress) return 'Waiting...';
    if (challengeType === 'typing') return (p.word_index || 0) + '/' + (p.total_words || 0) + ' words • ' + (p.wpm || 0) + ' WPM';
    if (challengeType === 'quiz') return sc + '/' + tg + ' correct';
    if (challengeType === 'cps') return sc + ' clicks';
    if (challengeType === 'aim3d') return sc + '/' + tg + ' pts';
    if (challengeType === 'reaction') return 'Attempt ' + (p.attempts_done || 0) + '/' + (p.total_attempts || 5);
    if (challengeType === 'memory') return 'Level ' + (p.current_level || 0);
    if (challengeType === 'runner') return sc + ' pts';
    if (challengeType === 'tictactoe') return (p.wins || 0) + '/' + (p.target_wins || 1) + ' wins';
    return Math.round(getProgressPercent()) + '%';
  };
  var getLiveText = function () {
    if (!isConnected) return 'Disconnected';
    if (!progress) return 'Waiting for first move...';
    if (challengeType === 'typing') return 'Typing at ' + (p.wpm || 0) + ' WPM';
    if (challengeType === 'quiz') return sc + '/' + tg;
    if (challengeType === 'cps') return 'Clicking!';
    if (challengeType === 'aim3d') return 'Aiming!';
    if (challengeType === 'reaction') return 'Reacting!';
    if (challengeType === 'memory') return 'Memorizing...';
    if (challengeType === 'runner') return 'Running!';
    if (challengeType === 'tictactoe') return 'Playing!';
    if (challengeType === 'coding') return 'Coding!';
    return 'Playing...';
  };
  const pct = Math.min(getProgressPercent(), 100);
  return /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    className: "opp-card"
  }, /*#__PURE__*/React.createElement("div", {
    className: "o-avatar"
  }, player.avatar ? /*#__PURE__*/React.createElement("img", {
    src: player.avatar,
    alt: ""
  }) : /*#__PURE__*/React.createElement("i", {
    className: "fas fa-user"
  })), /*#__PURE__*/React.createElement("div", {
    className: "o-name"
  }, player.display_name), /*#__PURE__*/React.createElement("div", {
    className: "o-rank"
  }, player.rank)), /*#__PURE__*/React.createElement("div", {
    className: "opp-progress"
  }, /*#__PURE__*/React.createElement("div", {
    className: "op-label"
  }, "Progress"), /*#__PURE__*/React.createElement("div", {
    className: "op-bar"
  }, /*#__PURE__*/React.createElement("div", {
    className: "op-bar-inner",
    style: {
      width: pct + '%'
    }
  })), /*#__PURE__*/React.createElement("div", {
    className: "op-val"
  }, getProgressText())), /*#__PURE__*/React.createElement("div", {
    className: "opp-live"
  }, /*#__PURE__*/React.createElement("i", {
    className: "fas fa-circle"
  }), " ", getLiveText()));
}

// ── COMPONENT: OpponentTrackers ──
function OpponentTrackers({
  players,
  challengeType,
  lastProgress,
  userId
}) {
  const opponents = players.filter(p => p.user_id !== userId);
  if (opponents.length === 0) return null;
  const allProgress = lastProgress || {};
  return opponents.map(p => /*#__PURE__*/React.createElement(PlayerTracker, {
    key: p.user_id,
    player: p,
    challengeType: challengeType,
    progress: allProgress[p.user_id] || {},
    isConnected: p.connected !== false
  }));
}

// ── COMPONENT: TypingChallenge ──
function TypingChallenge({
  challenge,
  onProgress,
  onComplete
}) {
  const [words, setWords] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [input, setInput] = useState('');
  const [startTime, setStartTime] = useState(null);
  const [wpm, setWpm] = useState(0);
  const [done, setDone] = useState(false);
  const [timeLeft, setTimeLeft] = useState(challenge.duration || 30);
  const [errors, setErrors] = useState({});
  const progressRef = useRef({
    index: 0,
    wpm: 0
  });
  const tickRef = useRef(null);
  useEffect(() => {
    if (challenge.passage) {
      setWords(challenge.passage.split(' ').map(w => w.trim()).filter(Boolean));
    }
  }, [challenge]);
  const finishChallenge = useCallback(() => {
    if (done) return;
    setDone(true);
    if (tickRef.current) clearInterval(tickRef.current);
    const elapsed = Math.max(1, (Date.now() - (startTime || Date.now())) / 1000);
    const finalWpm = Math.round(currentIndex / elapsed * 60);
    onComplete({
      wpm: finalWpm,
      words: currentIndex,
      total_words: words.length,
      accuracy: Math.round(currentIndex / Math.max(1, currentIndex + Object.keys(errors).length) * 100)
    });
  }, [done, startTime, currentIndex, words.length, errors, onComplete]);
  useEffect(() => {
    if (startTime && !done) {
      tickRef.current = setInterval(() => {
        const elapsed = (Date.now() - startTime) / 1000;
        const remaining = Math.max(0, (challenge.duration || 30) - elapsed);
        setTimeLeft(Math.ceil(remaining));
        if (remaining <= 0) {
          clearInterval(tickRef.current);
          finishChallenge();
        }
      }, 200);
    }
    return () => {
      if (tickRef.current) clearInterval(tickRef.current);
    };
  }, [startTime, done, finishChallenge]);
  useEffect(() => {
    if (words.length > 0 && currentIndex >= words.length && startTime && !done) {
      finishChallenge();
    }
  }, [currentIndex, words.length, startTime, done, finishChallenge]);
  useEffect(() => {
    if (startTime) {
      progressRef.current = {
        index: currentIndex,
        wpm
      };
      const pct = words.length > 0 ? currentIndex / words.length * 100 : 0;
      onProgress({
        word_index: currentIndex,
        total_words: words.length,
        wpm,
        percent_complete: pct
      });
    }
  }, [currentIndex, wpm, startTime]);
  const handleInput = e => {
    if (!startTime) setStartTime(Date.now());
    if (done) return;
    const val = e.target.value;
    setInput(val);
    const expectedWord = words[currentIndex];
    if (!expectedWord) return;
    if (val.endsWith(' ') || val.endsWith('  ')) {
      const typed = val.trim();
      if (typed === expectedWord) {
        setCurrentIndex(i => i + 1);
        setInput('');
        const elapsed = Math.max(1, (Date.now() - (startTime || Date.now())) / 1000);
        setWpm(Math.round((currentIndex + 1) / elapsed * 60));
      } else {
        setErrors(e => ({
          ...e,
          [currentIndex]: true
        }));
        setCurrentIndex(i => i + 1);
        setInput('');
      }
    }
  };
  return /*#__PURE__*/React.createElement("div", {
    className: "typing-game"
  }, /*#__PURE__*/React.createElement("div", {
    className: "passage"
  }, words.map((w, i) => /*#__PURE__*/React.createElement("span", {
    key: i,
    className: `word${i === currentIndex ? ' current' : ''}${i < currentIndex ? errors[i] ? ' error' : ' done' : ''}`
  }, w, ' '))), /*#__PURE__*/React.createElement("input", {
    className: "typing-input",
    value: input,
    onChange: handleInput,
    placeholder: done ? 'Finished!' : 'Type here...',
    disabled: done,
    autoFocus: true
  }), /*#__PURE__*/React.createElement("div", {
    className: "stats-row"
  }, /*#__PURE__*/React.createElement("div", {
    className: "stat"
  }, /*#__PURE__*/React.createElement("div", {
    className: "num"
  }, wpm), /*#__PURE__*/React.createElement("div", {
    className: "lbl"
  }, "WPM")), /*#__PURE__*/React.createElement("div", {
    className: "stat"
  }, /*#__PURE__*/React.createElement("div", {
    className: "num"
  }, currentIndex, "/", words.length), /*#__PURE__*/React.createElement("div", {
    className: "lbl"
  }, "Words")), /*#__PURE__*/React.createElement("div", {
    className: "stat"
  }, /*#__PURE__*/React.createElement("div", {
    className: "num"
  }, timeLeft, "s"), /*#__PURE__*/React.createElement("div", {
    className: "lbl"
  }, "Left"))));
}

// ── COMPONENT: QuizChallenge ──
function QuizChallenge({
  challenge,
  onProgress,
  onComplete
}) {
  const [index, setIndex] = useState(0);
  const [score, setScore] = useState(0);
  const [answered, setAnswered] = useState(false);
  const [selected, setSelected] = useState(-1);
  const [done, setDone] = useState(false);
  const questions = challenge.questions || [];
  const scoreRef = useRef(0);
  const startTimeRef = useRef(Date.now());
  useEffect(() => {
    if (questions.length > 0) {
      onProgress({
        question_index: index,
        total_questions: questions.length,
        is_correct: undefined,
        percent_complete: index / questions.length * 100
      });
    }
  }, []);
  const handleAnswer = optIdx => {
    if (answered) return;
    setAnswered(true);
    setSelected(optIdx);
    const correct = optIdx === questions[index].ans;
    const newScore = score + (correct ? 1 : 0);
    if (correct) setScore(newScore);
    scoreRef.current = newScore;
    onProgress({
      question_index: index + 1,
      total_questions: questions.length,
      is_correct: correct,
      percent_complete: (index + 1) / questions.length * 100
    });
    setTimeout(() => {
      if (index + 1 >= questions.length) {
        setDone(true);
        onComplete({
          score: newScore,
          total: questions.length,
          percent: Math.round(newScore / questions.length * 100)
        });
      } else {
        setIndex(i => i + 1);
        setAnswered(false);
        setSelected(-1);
        onProgress({
          question_index: index + 2,
          total_questions: questions.length,
          is_correct: undefined,
          percent_complete: (index + 2) / questions.length * 100
        });
      }
    }, 1200);
  };
  if (questions.length === 0) return /*#__PURE__*/React.createElement("div", {
    className: "quiz-game"
  }, /*#__PURE__*/React.createElement("p", {
    style: {
      color: 'rgba(0,0,0,0.4)'
    }
  }, "Loading questions..."));
  const q = questions[index];
  return /*#__PURE__*/React.createElement("div", {
    className: "quiz-game"
  }, /*#__PURE__*/React.createElement("div", {
    className: "q-num"
  }, "Question ", index + 1, " of ", questions.length), /*#__PURE__*/React.createElement("div", {
    className: "q-text"
  }, q.q), /*#__PURE__*/React.createElement("div", {
    className: "q-opts"
  }, q.opts.map((opt, i) => /*#__PURE__*/React.createElement("button", {
    key: i,
    className: `${answered && i === q.ans ? 'correct' : ''}${answered && i === selected && i !== q.ans ? 'wrong' : ''}`,
    onClick: () => handleAnswer(i),
    disabled: answered
  }, String.fromCharCode(65 + i), ". ", opt))), answered && /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 8,
      fontSize: '.75rem',
      color: 'rgba(0,0,0,0.4)'
    }
  }, index + 1 >= questions.length ? 'Showing results...' : 'Next question...'), /*#__PURE__*/React.createElement("div", {
    className: "q-score"
  }, score, "/", index + (answered ? 1 : 0)));
}

// ── COMPONENT: CpsChallenge ──
function CpsChallenge({
  challenge,
  onProgress,
  onComplete
}) {
  const [clicks, setClicks] = useState(0);
  const [timeLeft, setTimeLeft] = useState(challenge.time_limit || 10);
  const [active, setActive] = useState(false);
  const [done, setDone] = useState(false);
  const countRef = useRef(0);
  const startRef = useRef(null);
  useEffect(() => {
    if (!active || done) return;
    const timer = setInterval(() => {
      const elapsed = (Date.now() - startRef.current) / 1000;
      const remaining = Math.max(0, (challenge.time_limit || 10) - elapsed);
      setTimeLeft(Math.ceil(remaining));
      const current = countRef.current;
      const cps = Math.round(current / Math.max(1, elapsed) * 10) / 10;
      onProgress({
        current_score: current,
        target_score: challenge.target_score || 80,
        cps,
        time_remaining: Math.ceil(remaining),
        percent_complete: current / (challenge.target_score || 80) * 100
      });
      if (remaining <= 0) {
        clearInterval(timer);
        setDone(true);
        const finalElapsed = Math.max(1, elapsed);
        const finalCps = Math.round(current / finalElapsed * 10) / 10;
        onComplete({
          score: current,
          cps: finalCps,
          target: challenge.target_score || 80
        });
      }
    }, 200);
    return () => clearInterval(timer);
  }, [active, done]);
  const handleClick = () => {
    if (done) return;
    if (!active) {
      setActive(true);
      startRef.current = Date.now();
    }
    countRef.current += 1;
    setClicks(countRef.current);
  };
  return /*#__PURE__*/React.createElement("div", {
    className: "cps-game"
  }, /*#__PURE__*/React.createElement("div", {
    className: "cps-target"
  }, "Target: ", challenge.target_cps || '?', " CPS (", challenge.target_score || 80, " clicks in ", challenge.time_limit || 10, "s)"), /*#__PURE__*/React.createElement("button", {
    className: "cps-btn",
    onClick: handleClick,
    disabled: done
  }, done ? 'DONE' : 'CLICK!'), /*#__PURE__*/React.createElement("div", {
    className: "cps-stats"
  }, /*#__PURE__*/React.createElement("div", {
    className: "stat"
  }, /*#__PURE__*/React.createElement("div", {
    className: "num"
  }, clicks), /*#__PURE__*/React.createElement("div", {
    className: "lbl"
  }, "Clicks")), /*#__PURE__*/React.createElement("div", {
    className: "stat"
  }, /*#__PURE__*/React.createElement("div", {
    className: "num"
  }, active ? Math.round(clicks / Math.max(1, (Date.now() - startRef.current) / 1000) * 10) / 10 : 0), /*#__PURE__*/React.createElement("div", {
    className: "lbl"
  }, "CPS")), /*#__PURE__*/React.createElement("div", {
    className: "stat"
  }, /*#__PURE__*/React.createElement("div", {
    className: "num"
  }, timeLeft, "s"), /*#__PURE__*/React.createElement("div", {
    className: "lbl"
  }, "Left"))));
}

// ── COMPONENT: Aim3dChallenge ──
function Aim3dChallenge({
  challenge,
  onProgress,
  onComplete
}) {
  const [score, setScore] = useState(0);
  const [timeLeft, setTimeLeft] = useState(challenge.time_limit || 30);
  const [active, setActive] = useState(false);
  const [done, setDone] = useState(false);
  const [accuracy, setAccuracy] = useState(100);
  const [hits, setHits] = useState(0);
  const [misses, setMisses] = useState(0);
  const targetRef = useRef(null);
  const containerRef = useRef(null);
  const scoreRef = useRef(0);
  const hitsRef = useRef(0);
  const missesRef = useRef(0);
  const startRef = useRef(null);
  const animRef = useRef(null);
  const targetSizePreset = challenge.target_size || 'medium';
  const targetSpeedPreset = challenge.target_speed || 'normal';
  const targetScore = challenge.target_score || 1000;
  const timeLimit = challenge.time_limit || 30;
  const getTargetSize = () => {
    if (targetSizePreset === 'small') return 18 + Math.random() * 12;
    if (targetSizePreset === 'large') return 55 + Math.random() * 35;
    return 35 + Math.random() * 25;
  };
  const getMovement = () => {
    if (targetSpeedPreset === 'slow') return {
      dx: 0,
      dy: 0
    };
    if (targetSpeedPreset === 'fast') return {
      dx: (Math.random() - 0.5) * 3,
      dy: (Math.random() - 0.5) * 3
    };
    return {
      dx: (Math.random() - 0.5) * 1.2,
      dy: (Math.random() - 0.5) * 1.2
    };
  };
  useEffect(() => {
    if (!active || done) return;
    const timer = setInterval(() => {
      const elapsed = (Date.now() - startRef.current) / 1000;
      const remaining = Math.max(0, timeLimit - elapsed);
      setTimeLeft(Math.ceil(remaining));
      const current = scoreRef.current;
      const acc = hitsRef.current + missesRef.current > 0 ? Math.round(hitsRef.current / (hitsRef.current + missesRef.current) * 100) : 100;
      onProgress({
        current_score: current,
        target_score: targetScore,
        accuracy: acc,
        hits: hitsRef.current,
        percent_complete: current / targetScore * 100
      });
      if (remaining <= 0) {
        clearInterval(timer);
        setDone(true);
        onComplete({
          score: current,
          target: targetScore,
          accuracy: acc,
          hits: hitsRef.current
        });
      }
    }, 200);
    return () => clearInterval(timer);
  }, [active, done]);
  const spawnTarget = () => {
    if (!containerRef.current || done) return;
    const container = containerRef.current.getBoundingClientRect();
    const size = getTargetSize();
    const x = Math.random() * (container.width - size);
    const y = Math.random() * (container.height - size);
    const m = getMovement();
    return {
      x,
      y,
      size,
      id: Date.now() + Math.random(),
      dx: m.dx,
      dy: m.dy
    };
  };
  useEffect(() => {
    if (!active || done || !targetRef.current) return;
    let lastMove = Date.now();
    const moveInterval = targetSpeedPreset === 'fast' ? 30 : 60;
    const moveLoop = () => {
      if (!targetRef.current || done) return;
      if (targetRef.current.style.display !== 'none') {
        const now = Date.now();
        if (now - lastMove >= moveInterval) {
          lastMove = now;
          const t = targetRef.current._moveData;
          if (t) {
            const container = containerRef.current?.getBoundingClientRect();
            if (container) {
              t.x += t.dx || 0;
              t.y += t.dy || 0;
              if (t.x < 0) t.x = 0;
              if (t.y < 0) t.y = 0;
              if (t.x > container.width - t.size) t.x = container.width - t.size;
              if (t.y > container.height - t.size) t.y = container.height - t.size;
              targetRef.current.style.left = t.x + 'px';
              targetRef.current.style.top = t.y + 'px';
            }
          }
        }
      }
      if (!done) animRef.current = requestAnimationFrame(moveLoop);
    };
    animRef.current = requestAnimationFrame(moveLoop);
    return () => {
      if (animRef.current) cancelAnimationFrame(animRef.current);
    };
  }, [active, done, targetSpeedPreset]);
  const handleContainerClick = e => {
    if (done) return;
    if (!active) {
      setActive(true);
      startRef.current = Date.now();
    }
    missesRef.current += 1;
    setMisses(missesRef.current);
    const acc = Math.round(hitsRef.current / (hitsRef.current + missesRef.current) * 100);
    setAccuracy(acc);
  };
  const handleTargetClick = e => {
    e.stopPropagation();
    if (done) return;
    if (!active) {
      setActive(true);
      startRef.current = Date.now();
    }
    hitsRef.current += 1;
    scoreRef.current += 100;
    setHits(hitsRef.current);
    setScore(scoreRef.current);
    const acc = Math.round(hitsRef.current / (hitsRef.current + missesRef.current) * 100);
    setAccuracy(acc);
    const target = e.currentTarget;
    target.style.display = 'none';
    const t = spawnTarget();
    if (t) {
      target.style.left = t.x + 'px';
      target.style.top = t.y + 'px';
      target.style.width = t.size + 'px';
      target.style.height = t.size + 'px';
      target.style.display = 'block';
      target._moveData = t;
    }
  };
  useEffect(() => {
    if (containerRef.current && !done) {
      const t = spawnTarget();
      if (t && targetRef.current) {
        targetRef.current.style.left = t.x + 'px';
        targetRef.current.style.top = t.y + 'px';
        targetRef.current.style.width = t.size + 'px';
        targetRef.current.style.height = t.size + 'px';
        targetRef.current._moveData = t;
      }
    }
  }, [active, done]);
  return /*#__PURE__*/React.createElement("div", {
    style: {
      textAlign: 'center',
      width: '100%',
      maxWidth: 500
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 16,
      justifyContent: 'center',
      marginBottom: 10
    }
  }, /*#__PURE__*/React.createElement("div", {
    className: "stat"
  }, /*#__PURE__*/React.createElement("div", {
    className: "num",
    style: {
      fontSize: '1.2rem'
    }
  }, score), /*#__PURE__*/React.createElement("div", {
    className: "lbl"
  }, "Score")), /*#__PURE__*/React.createElement("div", {
    className: "stat"
  }, /*#__PURE__*/React.createElement("div", {
    className: "num",
    style: {
      fontSize: '1.2rem'
    }
  }, accuracy, "%"), /*#__PURE__*/React.createElement("div", {
    className: "lbl"
  }, "Accuracy")), /*#__PURE__*/React.createElement("div", {
    className: "stat"
  }, /*#__PURE__*/React.createElement("div", {
    className: "num",
    style: {
      fontSize: '1.2rem'
    }
  }, timeLeft, "s"), /*#__PURE__*/React.createElement("div", {
    className: "lbl"
  }, "Left"))), /*#__PURE__*/React.createElement("div", {
    ref: containerRef,
    onClick: handleContainerClick,
    style: {
      width: '100%',
      height: 280,
      borderRadius: 12,
      background: 'rgba(0,0,0,0.02)',
      border: '1px solid rgba(45,125,210,0.08)',
      position: 'relative',
      overflow: 'hidden',
      cursor: 'crosshair',
      margin: '0 auto'
    }
  }, /*#__PURE__*/React.createElement("div", {
    ref: targetRef,
    onClick: handleTargetClick,
    style: {
      position: 'absolute',
      borderRadius: '50%',
      background: 'radial-gradient(circle,#ff4757,#c0392b)',
      boxShadow: '0 0 20px rgba(255,71,87,0.4)',
      cursor: 'pointer',
      transition: 'none',
      display: active ? 'block' : 'none'
    }
  }), !active && !done && /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      color: 'rgba(0,0,0,0.35)',
      fontSize: '.85rem'
    }
  }, "Click anywhere to start"), done && /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      inset: 0,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      color: 'rgba(0,0,0,0.35)',
      fontSize: '1rem',
      fontWeight: 600
    }
  }, "Done! Score: ", score)));
}

// ── COMPONENT: ReactionChallenge ──
function ReactionChallenge({
  challenge,
  onProgress,
  onComplete
}) {
  const [state, setState] = useState('idle');
  const [attempts, setAttempts] = useState(0);
  const [times, setTimes] = useState([]);
  const [best, setBest] = useState(null);
  const [done, setDone] = useState(false);
  const lastTimeRef = useRef(0);
  const timeoutRef = useRef(null);
  const maxAttempts = challenge.attempts || 5;
  useEffect(() => {
    onProgress({
      attempts_done: 0,
      total_attempts: maxAttempts,
      best_time: null,
      avg_time: null,
      percent_complete: 0
    });
  }, []);
  const handleClick = () => {
    if (done) return;
    if (state === 'idle') {
      setState('waiting');
      const delay = 1000 + Math.random() * 3000;
      timeoutRef.current = setTimeout(() => {
        setState('ready');
        lastTimeRef.current = performance.now();
      }, delay);
    } else if (state === 'waiting') {
      clearTimeout(timeoutRef.current);
      setState('idle');
      // Too soon - count as attempt
      const newAttempts = attempts + 1;
      setAttempts(newAttempts);
      onProgress({
        attempts_done: newAttempts,
        total_attempts: maxAttempts,
        best_time: best,
        avg_time: times.length > 0 ? Math.round(times.reduce((a, b) => a + b, 0) / times.length) : null,
        percent_complete: newAttempts / maxAttempts * 100
      });
      if (newAttempts >= maxAttempts) {
        setDone(true);
        const avg = times.length > 0 ? Math.round(times.reduce((a, b) => a + b, 0) / times.length) : 999;
        onComplete({
          attempts: newAttempts,
          times: [...times, 999],
          best: best || 999,
          avg: avg,
          target: challenge.target_avg || 250
        });
      }
    } else if (state === 'ready') {
      const elapsed = Math.round(performance.now() - lastTimeRef.current);
      const newTimes = [...times, elapsed];
      const newBest = best === null ? elapsed : Math.min(best, elapsed);
      const newAttempts = attempts + 1;
      setTimes(newTimes);
      setBest(newBest);
      setAttempts(newAttempts);
      onProgress({
        attempts_done: newAttempts,
        total_attempts: maxAttempts,
        best_time: newBest,
        avg_time: Math.round(newTimes.reduce((a, b) => a + b, 0) / newTimes.length),
        percent_complete: newAttempts / maxAttempts * 100
      });
      setState('idle');
      if (newAttempts >= maxAttempts) {
        setDone(true);
        const avg = Math.round(newTimes.reduce((a, b) => a + b, 0) / newTimes.length);
        onComplete({
          attempts: newAttempts,
          times: newTimes,
          best: newBest,
          avg: avg,
          target: challenge.target_avg || 250
        });
      }
    }
  };
  const getColor = () => {
    if (state === 'waiting') return {
      bg: 'rgba(239,68,68,0.04)',
      border: 'rgba(239,68,68,0.1)'
    };
    if (state === 'ready') return {
      bg: 'rgba(34,197,94,0.04)',
      border: 'rgba(34,197,94,0.1)'
    };
    return {
      bg: 'rgba(0,0,0,0.015)',
      border: 'rgba(45,125,210,0.08)'
    };
  };
  const c = getColor();
  return /*#__PURE__*/React.createElement("div", {
    style: {
      textAlign: 'center',
      width: '100%',
      maxWidth: 450
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 16,
      justifyContent: 'center',
      marginBottom: 10
    }
  }, /*#__PURE__*/React.createElement("div", {
    className: "stat"
  }, /*#__PURE__*/React.createElement("div", {
    className: "num",
    style: {
      fontSize: '1.2rem'
    }
  }, best !== null ? best + 'ms' : '—'), /*#__PURE__*/React.createElement("div", {
    className: "lbl"
  }, "Best")), /*#__PURE__*/React.createElement("div", {
    className: "stat"
  }, /*#__PURE__*/React.createElement("div", {
    className: "num",
    style: {
      fontSize: '1.2rem'
    }
  }, attempts, "/", maxAttempts), /*#__PURE__*/React.createElement("div", {
    className: "lbl"
  }, "Attempts"))), /*#__PURE__*/React.createElement("div", {
    onClick: handleClick,
    style: {
      width: '100%',
      height: 180,
      borderRadius: 12,
      background: c.bg,
      border: `1px solid ${c.border}`,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      cursor: 'pointer',
      transition: 'all .2s'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: '1.1rem',
      fontWeight: 600,
      color: state === 'ready' ? '#22c55e' : state === 'waiting' ? '#f87171' : 'rgba(0,0,0,0.35)'
    }
  }, done ? 'Done!' : state === 'idle' ? 'Click to start' : state === 'waiting' ? 'Wait for green...' : 'CLICK NOW!')), done && /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 10,
      fontSize: '.8rem',
      color: 'rgba(0,0,0,0.4)'
    }
  }, "Avg: ", times.length > 0 ? Math.round(times.reduce((a, b) => a + b, 0) / times.length) : 0, "ms | Best: ", best, "ms"));
}

// ── COMPONENT: MemoryChallenge ──
function MemoryChallenge({
  challenge,
  onProgress,
  onComplete
}) {
  const [sequence, setSequence] = useState([]);
  const [playerIdx, setPlayerIdx] = useState(0);
  const [level, setLevel] = useState(0);
  const [phase, setPhase] = useState('start');
  const [done, setDone] = useState(false);
  const [litCell, setLitCell] = useState(-1);
  const seqRef = useRef([]);
  const levelRef = useRef(0);
  const targetLevel = challenge.target_level || 8;
  const gridSize = challenge.grid_size || 3;
  const cellCount = gridSize * gridSize;
  const palette = ['#ef4444', '#3b82f6', '#22c55e', '#eab308', '#a855f7', '#ec4899', '#f97316', '#14b8a6', '#6366f1', '#84cc16', '#06b6d4', '#d946ef', '#f43f5e', '#8b5cf6', '#10b981', '#e11d48'];
  const cellColors = palette.slice(0, cellCount);
  useEffect(() => {
    onProgress({
      current_level: 0,
      target_level: targetLevel,
      percent_complete: 0
    });
  }, []);
  const addAndShow = () => {
    const newSeq = [...seqRef.current, Math.floor(Math.random() * cellCount)];
    seqRef.current = newSeq;
    setSequence(newSeq);
    const newLevel = levelRef.current + 1;
    levelRef.current = newLevel;
    setLevel(newLevel);
    setPhase('showing');
    onProgress({
      current_level: newLevel,
      target_level: targetLevel,
      percent_complete: newLevel / targetLevel * 100
    });
    let i = 0;
    const showNext = () => {
      if (i >= newSeq.length) {
        setLitCell(-1);
        setPhase('input');
        setPlayerIdx(0);
        return;
      }
      setLitCell(newSeq[i]);
      i++;
      setTimeout(showNext, 500 + (i < newSeq.length ? 300 : 600));
    };
    setTimeout(showNext, 400);
  };
  const startGame = () => {
    seqRef.current = [];
    levelRef.current = 0;
    setLevel(0);
    setDone(false);
    setPhase('showing');
    addAndShow();
  };
  const handleCellClick = idx => {
    if (phase !== 'input' || done) return;
    const expected = sequence[playerIdx];
    if (idx === expected) {
      const nextIdx = playerIdx + 1;
      setPlayerIdx(nextIdx);
      if (nextIdx >= sequence.length) {
        setPhase('showing');
        if (level >= targetLevel) {
          setDone(true);
          onComplete({
            level: level,
            target: targetLevel,
            passed: true
          });
          return;
        }
        setTimeout(addAndShow, 500);
      }
    } else {
      setDone(true);
      onComplete({
        level: level - 1,
        target: targetLevel,
        passed: false
      });
    }
  };
  return /*#__PURE__*/React.createElement("div", {
    style: {
      textAlign: 'center',
      width: '100%',
      maxWidth: 320
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 16,
      justifyContent: 'center',
      marginBottom: 10
    }
  }, /*#__PURE__*/React.createElement("div", {
    className: "stat"
  }, /*#__PURE__*/React.createElement("div", {
    className: "num",
    style: {
      fontSize: '1.2rem'
    }
  }, level, "/", targetLevel), /*#__PURE__*/React.createElement("div", {
    className: "lbl"
  }, "Level"))), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'grid',
      gridTemplateColumns: `1fr 1fr 1fr`.slice(0, -2 * (3 - gridSize)),
      gap: 6,
      maxWidth: gridSize === 2 ? 160 : gridSize === 3 ? 240 : 320,
      margin: '0 auto'
    }
  }, Array.from({
    length: cellCount
  }, (_, i) => i).map(i => /*#__PURE__*/React.createElement("div", {
    key: i,
    onClick: () => handleCellClick(i),
    style: {
      aspectRatio: 1,
      borderRadius: 8,
      cursor: phase === 'input' ? 'pointer' : 'default',
      background: cellColors[i],
      opacity: litCell === i ? 1 : phase === 'input' ? 0.7 : 0.3,
      transform: litCell === i ? 'scale(1.08)' : 'scale(1)',
      transition: 'all .15s',
      border: litCell === i ? '2px solid rgba(255,255,255,0.3)' : '2px solid transparent'
    }
  }))), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 10,
      fontSize: '.8rem',
      color: 'rgba(0,0,0,0.4)'
    }
  }, phase === 'start' ? /*#__PURE__*/React.createElement("button", {
    onClick: startGame,
    style: {
      padding: '8px 24px',
      borderRadius: 10,
      border: 'none',
      background: 'linear-gradient(180deg,#2d7dd2,#1a5276)',
      color: '#fff',
      cursor: 'pointer',
      fontFamily: 'inherit',
      fontWeight: 600
    }
  }, "Start") : phase === 'showing' ? 'Watch...' : phase === 'input' ? 'Your turn!' : ''));
}

// ── COMPONENT: RunnerChallenge ──
function RunnerChallenge({
  challenge,
  onProgress,
  onComplete
}) {
  const [score, setScore] = useState(0);
  const [timeLeft, setTimeLeft] = useState(challenge.time_limit || 60);
  const [active, setActive] = useState(false);
  const [done, setDone] = useState(false);
  const [distance, setDistance] = useState(0);
  const [livesLeft, setLivesLeft] = useState(challenge.lives || 3);
  const canvasRef = useRef(null);
  const playerRef = useRef({
    x: 50,
    y: 280,
    vx: 0,
    vy: 0,
    w: 20,
    h: 30
  });
  const obstaclesRef = useRef([]);
  const scoreRef = useRef(0);
  const distanceRef = useRef(0);
  const livesRef = useRef(challenge.lives || 3);
  const startRef = useRef(null);
  const frameRef = useRef(null);
  const keysRef = useRef({});
  const maxLives = challenge.lives || 3;
  const difficulty = challenge.difficulty || 'normal';
  const targetScore = challenge.target_score || 5000;
  const timeLimit = challenge.time_limit || 60;
  const diffMul = difficulty === 'easy' ? 0.6 : difficulty === 'hard' ? 1.5 : 1;
  useEffect(() => {
    const handleKey = e => {
      keysRef.current[e.key] = e.type === 'keydown';
      if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', ' '].includes(e.key)) e.preventDefault();
    };
    document.addEventListener('keydown', handleKey);
    document.addEventListener('keyup', handleKey);
    return () => {
      document.removeEventListener('keydown', handleKey);
      document.removeEventListener('keyup', handleKey);
      if (frameRef.current) cancelAnimationFrame(frameRef.current);
    };
  }, []);
  const startGame = () => {
    setActive(true);
    setDone(false);
    livesRef.current = maxLives;
    setLivesLeft(maxLives);
    startRef.current = Date.now();
    scoreRef.current = 0;
    distanceRef.current = 0;
    obstaclesRef.current = [];
    playerRef.current = {
      x: 50,
      y: 280,
      vx: 0,
      vy: 0,
      w: 20,
      h: 30
    };
    frameRef.current = requestAnimationFrame(gameLoop);
  };
  const gameLoop = () => {
    if (!canvasRef.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const W = canvas.width = 400;
    const H = canvas.height = 250;
    const p = playerRef.current;
    const keys = keysRef.current;
    p.vy += 0.6;
    if ((keys['ArrowUp'] || keys['w'] || keys[' ']) && p.y >= 280) {
      p.vy = -10;
      p.y = 280;
    }
    if (keys['ArrowLeft'] || keys['a']) p.vx = -3;else if (keys['ArrowRight'] || keys['d']) p.vx = 3;else p.vx *= 0.9;
    p.x += p.vx;
    p.y += p.vy;
    if (p.x < 0) p.x = 0;
    if (p.x > W - p.w) p.x = W - p.w;
    if (p.y > 280) {
      p.y = 280;
      p.vy = 0;
    }
    distanceRef.current += 0.5;
    setDistance(Math.floor(distanceRef.current));
    const baseSpawn = 0.02 * diffMul;
    if (Math.random() < baseSpawn) {
      obstaclesRef.current.push({
        x: W,
        y: 280 - 20,
        w: 15,
        h: 20,
        vx: (-2 - scoreRef.current / 5000) * diffMul
      });
    }
    if (Math.random() < baseSpawn * 0.5) {
      obstaclesRef.current.push({
        x: W,
        y: 280 - 35,
        w: 15,
        h: 15,
        vx: (-2 - scoreRef.current / 5000) * diffMul,
        flying: true
      });
    }
    for (let i = obstaclesRef.current.length - 1; i >= 0; i--) {
      const o = obstaclesRef.current[i];
      o.x += o.vx;
      if (o.x < -50) {
        obstaclesRef.current.splice(i, 1);
        scoreRef.current += 10;
      }
    }
    for (let i = obstaclesRef.current.length - 1; i >= 0; i--) {
      const o = obstaclesRef.current[i];
      if (p.x < o.x + o.w && p.x + p.w > o.x && p.y < o.y + o.h && p.y + p.h > o.y) {
        obstaclesRef.current.splice(i, 1);
        livesRef.current -= 1;
        setLivesLeft(livesRef.current);
        if (livesRef.current <= 0) {
          setDone(true);
          setActive(false);
          setScore(scoreRef.current);
          if (frameRef.current) cancelAnimationFrame(frameRef.current);
          onComplete({
            score: scoreRef.current,
            distance: Math.floor(distanceRef.current),
            target: targetScore,
            lives_used: maxLives
          });
          return;
        }
      }
    }
    const elapsed = (Date.now() - startRef.current) / 1000;
    const remaining = Math.max(0, timeLimit - elapsed);
    setTimeLeft(Math.ceil(remaining));
    setScore(scoreRef.current);
    onProgress({
      current_score: scoreRef.current,
      target_score: targetScore,
      distance: Math.floor(distanceRef.current),
      time_remaining: Math.ceil(remaining),
      lives: livesRef.current,
      percent_complete: scoreRef.current / targetScore * 100
    });
    if (remaining <= 0) {
      setDone(true);
      setActive(false);
      if (frameRef.current) cancelAnimationFrame(frameRef.current);
      onComplete({
        score: scoreRef.current,
        distance: Math.floor(distanceRef.current),
        target: targetScore,
        lives_remaining: livesRef.current
      });
      return;
    }
    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = '#eef1f5';
    ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = '#2a2a3a';
    ctx.fillRect(0, 290, W, 10);
    ctx.fillStyle = '#e63946';
    ctx.fillRect(p.x, p.y, p.w, p.h);
    ctx.fillStyle = '#ffd6b3';
    ctx.fillRect(p.x + 3, p.y - 5, 14, 8);
    ctx.fillStyle = '#ff4757';
    for (const o of obstaclesRef.current) {
      ctx.fillRect(o.x, o.y, o.w, o.h);
      if (o.flying) {
        ctx.fillStyle = '#f7c948';
        ctx.fillRect(o.x - 5, o.y - 3, o.w + 10, 4);
        ctx.fillStyle = '#ff4757';
      }
    }
    ctx.fillStyle = '#fff';
    ctx.font = '10px sans-serif';
    ctx.fillText('Score: ' + scoreRef.current, 10, 15);
    frameRef.current = requestAnimationFrame(gameLoop);
  };
  return /*#__PURE__*/React.createElement("div", {
    style: {
      textAlign: 'center',
      width: '100%',
      maxWidth: 450
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 12,
      justifyContent: 'center',
      marginBottom: 10
    }
  }, /*#__PURE__*/React.createElement("div", {
    className: "stat"
  }, /*#__PURE__*/React.createElement("div", {
    className: "num",
    style: {
      fontSize: '1rem'
    }
  }, score), /*#__PURE__*/React.createElement("div", {
    className: "lbl"
  }, "Score")), /*#__PURE__*/React.createElement("div", {
    className: "stat"
  }, /*#__PURE__*/React.createElement("div", {
    className: "num",
    style: {
      fontSize: '1rem'
    }
  }, distance), /*#__PURE__*/React.createElement("div", {
    className: "lbl"
  }, "Dist")), /*#__PURE__*/React.createElement("div", {
    className: "stat"
  }, /*#__PURE__*/React.createElement("div", {
    className: "num",
    style: {
      fontSize: '1rem'
    }
  }, timeLeft, "s"), /*#__PURE__*/React.createElement("div", {
    className: "lbl"
  }, "Left")), /*#__PURE__*/React.createElement("div", {
    className: "stat"
  }, /*#__PURE__*/React.createElement("div", {
    className: "num",
    style: {
      fontSize: '1rem',
      color: '#ff4757'
    }
  }, '♥'.repeat(livesLeft), '♡'.repeat(maxLives - livesLeft)), /*#__PURE__*/React.createElement("div", {
    className: "lbl"
  }, "Lives"))), /*#__PURE__*/React.createElement("canvas", {
    ref: canvasRef,
    style: {
      width: '100%',
      maxWidth: 400,
      borderRadius: 12,
      background: '#eef1f5',
      border: '1px solid rgba(45,125,210,0.1)',
      margin: '0 auto',
      cursor: 'pointer'
    },
    onClick: active ? undefined : startGame
  }), !active && !done && /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 8,
      fontSize: '.8rem',
      color: 'rgba(0,0,0,0.4)'
    }
  }, "Click canvas to start! Arrow keys / Space to jump"), done && /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 8,
      fontSize: .8,
      color: '#f7c948',
      fontWeight: 600
    }
  }, "Score: ", score, " | Distance: ", distance));
}

// ── COMPONENT: TictactoeChallenge ──
function TictactoeChallenge({
  challenge,
  onProgress,
  onComplete
}) {
  const [board, setBoard] = useState(Array(9).fill(''));
  const [turn, setTurn] = useState('X');
  const [wins, setWins] = useState(0);
  const [losses, setLosses] = useState(0);
  const [draws, setDraws] = useState(0);
  const [gameActive, setGameActive] = useState(true);
  const [done, setDone] = useState(false);
  const [message, setMessage] = useState('Your turn (X)');
  const targetWins = challenge.target_wins || 1;
  const difficulty = challenge.difficulty || 'medium';
  const boardRef = useRef(board);
  const winsRef = useRef(0);
  const winCombos = [[0, 1, 2], [3, 4, 5], [6, 7, 8], [0, 3, 6], [1, 4, 7], [2, 5, 8], [0, 4, 8], [2, 4, 6]];
  const checkWin = b => {
    for (const c of winCombos) {
      if (b[c[0]] && b[c[0]] === b[c[1]] && b[c[0]] === b[c[2]]) return c;
    }
    return null;
  };
  useEffect(() => {
    onProgress({
      wins: 0,
      target_wins: targetWins,
      losses: 0,
      draws: 0,
      percent_complete: 0
    });
  }, []);
  const makeMove = idx => {
    if (!gameActive || board[idx] !== '' || turn !== 'X' || done) return;
    const newBoard = [...board];
    newBoard[idx] = 'X';
    setBoard(newBoard);
    boardRef.current = newBoard;
    const result = checkWin(newBoard);
    if (result) {
      const newWins = wins + 1;
      winsRef.current = newWins;
      setWins(newWins);
      setGameActive(false);
      setMessage('You win!');
      onProgress({
        wins: newWins,
        target_wins: targetWins,
        losses,
        draws,
        percent_complete: newWins / targetWins * 100
      });
      if (newWins >= targetWins) {
        setDone(true);
        onComplete({
          wins: newWins,
          losses,
          draws,
          target: targetWins,
          passed: true
        });
      } else {
        setTimeout(resetBoard, 1500);
      }
      return;
    }
    if (newBoard.every(c => c !== '')) {
      const newDraws = draws + 1;
      setDraws(newDraws);
      setGameActive(false);
      setMessage('Draw!');
      onProgress({
        wins: winsRef.current,
        target_wins: targetWins,
        losses,
        draws: newDraws,
        percent_complete: winsRef.current / targetWins * 100
      });
      setTimeout(resetBoard, 1500);
      return;
    }
    setTurn('O');
    setMessage('AI thinking...');
    setTimeout(() => aiMove(newBoard), 400);
  };
  const minimax = (b, isMax) => {
    const result = checkWin(b);
    if (result) {
      const winner = b[result[0]];
      return winner === 'O' ? 10 : -10;
    }
    if (b.every(c => c !== '')) return 0;
    const scores = [];
    for (let i = 0; i < 9; i++) {
      if (b[i] === '') {
        const test = [...b];
        test[i] = isMax ? 'O' : 'X';
        scores.push({
          score: minimax(test, !isMax),
          idx: i
        });
      }
    }
    if (scores.length === 0) return 0;
    if (isMax) return scores.reduce((best, s) => s.score > best.score ? s : best).score;
    return scores.reduce((best, s) => s.score < best.score ? s : best).score;
  };
  const aiMove = b => {
    if (done) return;
    if (difficulty === 'easy') {
      const empty = [];
      for (let i = 0; i < 9; i++) {
        if (b[i] === '') empty.push(i);
      }
      if (empty.length > 0) {
        applyAIMove(empty[Math.floor(Math.random() * empty.length)], b);
        return;
      }
      return;
    }
    if (difficulty === 'hard') {
      let bestIdx = -1,
        bestScore = -Infinity;
      for (let i = 0; i < 9; i++) {
        if (b[i] === '') {
          const test = [...b];
          test[i] = 'O';
          const s = minimax(test, false);
          if (s > bestScore) {
            bestScore = s;
            bestIdx = i;
          }
        }
      }
      if (bestIdx >= 0) {
        applyAIMove(bestIdx, b);
        return;
      }
      return;
    }
    // Medium: try to win, block, center, random
    for (let i = 0; i < 9; i++) {
      if (b[i] === '') {
        const test = [...b];
        test[i] = 'O';
        if (checkWin(test)) {
          applyAIMove(i, b);
          return;
        }
      }
    }
    for (let i = 0; i < 9; i++) {
      if (b[i] === '') {
        const test = [...b];
        test[i] = 'X';
        if (checkWin(test)) {
          applyAIMove(i, b);
          return;
        }
      }
    }
    if (b[4] === '') {
      applyAIMove(4, b);
      return;
    }
    const empty = [];
    for (let i = 0; i < 9; i++) {
      if (b[i] === '') empty.push(i);
    }
    if (empty.length > 0) applyAIMove(empty[Math.floor(Math.random() * empty.length)], b);
  };
  const applyAIMove = (idx, b) => {
    const newBoard = [...b];
    newBoard[idx] = 'O';
    setBoard(newBoard);
    boardRef.current = newBoard;
    const result = checkWin(newBoard);
    if (result) {
      const newLosses = losses + 1;
      setLosses(newLosses);
      setGameActive(false);
      setMessage('AI wins!');
      onProgress({
        wins: winsRef.current,
        target_wins: targetWins,
        losses: newLosses,
        draws,
        percent_complete: winsRef.current / targetWins * 100
      });
      setTimeout(resetBoard, 1500);
      return;
    }
    if (newBoard.every(c => c !== '')) {
      const newDraws = draws + 1;
      setDraws(newDraws);
      setGameActive(false);
      setMessage('Draw!');
      onProgress({
        wins: winsRef.current,
        target_wins: targetWins,
        losses,
        draws: newDraws,
        percent_complete: winsRef.current / targetWins * 100
      });
      setTimeout(resetBoard, 1500);
      return;
    }
    setTurn('X');
    setMessage('Your turn (X)');
  };
  const resetBoard = () => {
    setBoard(Array(9).fill(''));
    setTurn('X');
    setGameActive(true);
    setMessage('Your turn (X)');
  };
  const getCell = i => {
    const val = board[i];
    let cls = '';
    if (val === 'X') cls = 'color:#a855f7;text-shadow:0 0 10px rgba(168,85,247,0.3)';
    if (val === 'O') cls = 'color:#22c55e;text-shadow:0 0 10px rgba(34,197,94,0.3)';
    return /*#__PURE__*/React.createElement("div", {
      key: i,
      onClick: () => makeMove(i),
      style: {
        aspectRatio: 1,
        borderRadius: 10,
        background: 'var(--surface)',
        border: '1px solid rgba(45,125,210,0.08)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: '2rem',
        fontWeight: 700,
        cursor: val === '' && gameActive && turn === 'X' ? 'pointer' : 'default',
        transition: 'all .2s',
        opacity: done ? 0.6 : 1
      }
    }, /*#__PURE__*/React.createElement("span", {
      style: val === 'X' ? {
        color: '#a855f7',
        textShadow: '0 0 10px rgba(168,85,247,0.3)'
      } : val === 'O' ? {
        color: '#22c55e',
        textShadow: '0 0 10px rgba(34,197,94,0.3)'
      } : {}
    }, val));
  };
  return /*#__PURE__*/React.createElement("div", {
    style: {
      textAlign: 'center',
      width: '100%',
      maxWidth: 300
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 12,
      justifyContent: 'center',
      marginBottom: 10
    }
  }, /*#__PURE__*/React.createElement("div", {
    className: "stat"
  }, /*#__PURE__*/React.createElement("div", {
    className: "num",
    style: {
      fontSize: '1rem'
    }
  }, wins, "/", targetWins), /*#__PURE__*/React.createElement("div", {
    className: "lbl"
  }, "Wins")), /*#__PURE__*/React.createElement("div", {
    className: "stat"
  }, /*#__PURE__*/React.createElement("div", {
    className: "num",
    style: {
      fontSize: '1rem'
    }
  }, losses), /*#__PURE__*/React.createElement("div", {
    className: "lbl"
  }, "Losses")), /*#__PURE__*/React.createElement("div", {
    className: "stat"
  }, /*#__PURE__*/React.createElement("div", {
    className: "num",
    style: {
      fontSize: '1rem'
    }
  }, draws), /*#__PURE__*/React.createElement("div", {
    className: "lbl"
  }, "Draws"))), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'grid',
      gridTemplateColumns: '1fr 1fr 1fr',
      gap: 6,
      maxWidth: 200,
      margin: '0 auto'
    }
  }, [0, 1, 2, 3, 4, 5, 6, 7, 8].map(getCell)), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 8,
      fontSize: '.8rem',
      color: 'rgba(0,0,0,0.4)'
    }
  }, message));
}

// ── COMPONENT: ChallengeGame ──
function ChallengeGame({
  challenge,
  challengeType,
  roomCode,
  onProgress,
  onComplete,
  onOpponentProgress,
  onSubmitCode,
  onTypingScreenshot,
  players,
  userId
}) {
  const iframeRef = useRef(null);
  const challengeRef = useRef(challenge);
  challengeRef.current = challenge;
  const supportedGames = ['typing', 'quiz', 'cps', 'aim3d', 'reaction', 'memory', 'runner', 'tictactoe'];
  const hasTemplate = supportedGames.includes(challengeType);
  const iframeSrc = hasTemplate ? `/multiplayer-game/${challengeType}/?room=${roomCode}&target=${challenge?.target_level || challenge?.target_score || 10}` : null;
  const opponentName = players?.find(p => p.user_id !== userId)?.display_name || 'Opponent';
  const lastOpponentProgressRef = useRef(null);
  const startedRef = useRef(false);
  useEffect(() => {
    var logo = document.querySelector('.mp-logo');
    if (logo) logo.style.display = 'none';
    return () => {
      if (logo) logo.style.display = '';
    };
  }, []);
  const sendStart = () => {
    if (startedRef.current) return;
    startedRef.current = true;
    try {
      var chal = Object.assign({}, challengeRef.current || {});
      chal.opponent_name = opponentName;
      iframeRef.current.contentWindow.postMessage({
        type: 'start',
        challenge: chal,
        players: players,
        userId: userId
      }, '*');
      var opp = players?.find(p => p.user_id !== userId);
      if (opp) {
        var oppUserId = opp.user_id;
        var oppProg = onOpponentProgress?.[oppUserId] || {};
        iframeRef.current.contentWindow.postMessage({
          type: 'opponent_info',
          opp: {
            display_name: opp.display_name,
            avatar: opp.avatar,
            rank: opp.rank
          }
        }, '*');
        iframeRef.current.contentWindow.postMessage({
          type: 'opponent_progress',
          data: oppProg
        }, '*');
      }
    } catch (ex) {}
  };
  useEffect(() => {
    const handler = e => {
      const msg = e.data || {};
      if (msg.type === 'progress') {
        onProgress(msg.data);
      } else if (msg.type === 'complete') {
        onComplete(msg.data);
      } else if (msg.type === 'typing_screenshot' && onTypingScreenshot) {
        onTypingScreenshot(msg.screenshot, msg.result);
      } else if (msg.type === 'ready') {
        setTimeout(sendStart, 100);
      }
    };
    window.addEventListener('message', handler);
    return () => window.removeEventListener('message', handler);
  }, [onProgress, onComplete, onTypingScreenshot, sendStart]);
  useEffect(() => {
    if (!iframeRef.current) return;
    const handleLoad = () => {
      setTimeout(sendStart, 100);
    };
    iframeRef.current.addEventListener('load', handleLoad);
    return () => {
      iframeRef.current?.removeEventListener('load', handleLoad);
    };
  }, [sendStart]);
  useEffect(() => {
    if (!iframeRef.current || !onOpponentProgress || !players || !userId) return;
    var oppUserId = players.find(p => p.user_id !== userId)?.user_id;
    if (oppUserId && onOpponentProgress[oppUserId]) {
      try {
        var prog = onOpponentProgress[oppUserId];
        if (JSON.stringify(lastOpponentProgressRef.current) !== JSON.stringify(prog)) {
          lastOpponentProgressRef.current = prog;
          iframeRef.current.contentWindow.postMessage({
            type: 'opponent_progress',
            data: prog
          }, '*');
        }
      } catch (e) {}
    }
  }, [onOpponentProgress, players, userId]);
  if (challengeType === 'coding') {
    return /*#__PURE__*/React.createElement(CodingChallenge, {
      challenge: challenge,
      onSubmitCode: onSubmitCode
    });
  }
  if (!hasTemplate) {
    return /*#__PURE__*/React.createElement("div", {
      style: {
        color: 'rgba(0,0,0,0.4)',
        textAlign: 'center',
        padding: 40
      }
    }, "Loading game...");
  }
  return /*#__PURE__*/React.createElement("iframe", {
    ref: iframeRef,
    src: iframeSrc,
    style: {
      position: 'absolute',
      inset: 0,
      width: '100%',
      height: '100%',
      border: 'none',
      background: '#0a0a0f',
      display: 'block'
    }
  });
}

// ── COMPONENT: CodingChallenge ──
function CodingChallenge({
  challenge,
  onSubmitCode
}) {
  const [code, setCode] = useState('#include <iostream>\nusing namespace std;\n\nint main() {\n  \n  return 0;\n}');
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState(null);
  const [done, setDone] = useState(false);
  const [result, setResult] = useState(null);
  useEffect(() => {
    const handler = e => {
      const data = e.detail;
      setSubmitting(false);
      setFeedback(data);
      if (data.passed) {
        setDone(true);
        setResult('won');
      }
    };
    window.addEventListener('code_result', handler);
    return () => window.removeEventListener('code_result', handler);
  }, []);
  const handleSubmit = () => {
    if (!code.trim() || submitting || done) return;
    setSubmitting(true);
    setFeedback(null);
    onSubmitCode(code);
  };
  const handleKeyDown = e => {
    if (e.key === 'Tab') {
      e.preventDefault();
      const start = e.target.selectionStart;
      const end = e.target.selectionEnd;
      const val = e.target.value;
      e.target.value = val.substring(0, start) + '  ' + val.substring(end);
      e.target.selectionStart = e.target.selectionEnd = start + 2;
      setCode(e.target.value);
    }
  };
  return /*#__PURE__*/React.createElement("div", {
    style: {
      width: '100%',
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      background: 'var(--surface)',
      borderRadius: 12,
      overflow: 'hidden',
      border: '1px solid rgba(45,125,210,0.1)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '16px 20px',
      borderBottom: '1px solid rgba(45,125,210,0.1)',
      background: 'var(--surface)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: '10px',
      fontWeight: 700,
      color: '#2d7dd2',
      textTransform: 'uppercase',
      letterSpacing: '1px',
      marginBottom: 6
    }
  }, /*#__PURE__*/React.createElement("i", {
    className: "fas fa-code"
  }), " C++ Challenge"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: '14px',
      color: '#2a2a3a',
      fontWeight: 600,
      lineHeight: 1.5
    }
  }, challenge?.problem || 'Write a C++ program.')), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      position: 'relative',
      overflow: 'hidden'
    }
  }, /*#__PURE__*/React.createElement("textarea", {
    value: code,
    onChange: e => setCode(e.target.value),
    onKeyDown: handleKeyDown,
    disabled: done,
    spellCheck: false,
    style: {
      width: '100%',
      height: '100%',
      resize: 'none',
      border: 'none',
      outline: 'none',
      background: 'var(--surface)',
      color: '#2a2a3a',
      fontFamily: "'Courier New',monospace",
      fontSize: '13px',
      lineHeight: 1.7,
      padding: '16px 20px',
      tabSize: 2
    },
    placeholder: "Write your C++ code here..."
  })), feedback && /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '10px 16px',
      borderTop: '1px solid rgba(45,125,210,0.08)',
      background: feedback.passed ? 'rgba(34,197,94,0.06)' : 'rgba(255,71,87,0.06)',
      color: feedback.passed ? '#22c55e' : '#ff4757',
      fontSize: '13px',
      fontWeight: 600,
      display: 'flex',
      alignItems: 'center',
      gap: 8
    }
  }, /*#__PURE__*/React.createElement("i", {
    className: `fas ${feedback.passed ? 'fa-check-circle' : 'fa-times-circle'}`
  }), feedback.feedback || (feedback.passed ? 'Correct!' : 'Incorrect.')), /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '12px 16px',
      borderTop: '1px solid rgba(45,125,210,0.08)',
      display: 'flex',
      gap: 8,
      alignItems: 'center',
      background: 'var(--surface)'
    }
  }, /*#__PURE__*/React.createElement("button", {
    onClick: handleSubmit,
    disabled: submitting || done || !code.trim(),
    style: {
      flex: 1,
      padding: '10px 0',
      borderRadius: 8,
      border: 'none',
      cursor: 'pointer',
      fontWeight: 700,
      fontSize: '13px',
      fontFamily: 'inherit',
      background: done ? 'rgba(34,197,94,0.2)' : 'linear-gradient(135deg,#1a5276,#2d7dd2)',
      color: done ? '#22c55e' : '#fff',
      opacity: submitting ? 0.6 : 1
    }
  }, submitting ? /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("i", {
    className: "fas fa-spinner fa-spin"
  }), " Checking...") : done ? /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("i", {
    className: "fas fa-check"
  }), " Submitted!") : /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("i", {
    className: "fas fa-paper-plane"
  }), " Submit Code"))));
}

// ── COMPONENT: ChallengeSettings ──
function ChallengeSettings({
  challengeType,
  currentSettings,
  onChange,
  isCreator
}) {
  const [local, setLocal] = useState(currentSettings || getDefaultSettings(challengeType));
  const prevTypeRef = useRef(challengeType);
  useEffect(() => {
    if (prevTypeRef.current !== challengeType) {
      const def = getDefaultSettings(challengeType);
      setLocal(def);
      onChange(def);
      prevTypeRef.current = challengeType;
    }
  }, [challengeType]);
  useEffect(() => {
    if (currentSettings) setLocal(currentSettings);
  }, [currentSettings]);
  const update = (key, val) => {
    if (!isCreator) return;
    const next = {
      ...local,
      [key]: val
    };
    setLocal(next);
    onChange(next);
  };
  const renderField = (label, key, options) => /*#__PURE__*/React.createElement("div", {
    className: "settings-field",
    key: key
  }, /*#__PURE__*/React.createElement("span", {
    className: "settings-label"
  }, label), /*#__PURE__*/React.createElement("div", {
    className: "settings-options"
  }, options.map(o => /*#__PURE__*/React.createElement("button", {
    key: o.value,
    className: `settings-opt${local[key] === o.value ? ' active' : ''}`,
    onClick: () => update(key, o.value),
    disabled: !isCreator
  }, o.label))));
  const renderRange = (label, key, min, max, step) => /*#__PURE__*/React.createElement("div", {
    className: "settings-field"
  }, /*#__PURE__*/React.createElement("span", {
    className: "settings-label"
  }, label, ": ", /*#__PURE__*/React.createElement("strong", null, local[key])), /*#__PURE__*/React.createElement("input", {
    type: "range",
    min: min,
    max: max,
    step: step || 1,
    value: local[key] || min,
    onChange: e => update(key, Number(e.target.value)),
    disabled: !isCreator
  }));
  const settingsUI = {
    typing: () => /*#__PURE__*/React.createElement(React.Fragment, null, renderField('Duration', 'duration', [{
      label: '15s',
      value: 15
    }, {
      label: '30s',
      value: 30
    }, {
      label: '60s',
      value: 60
    }, {
      label: '120s',
      value: 120
    }]), renderRange('Target WPM', 'target_wpm', 20, 100, 5)),
    quiz: () => /*#__PURE__*/React.createElement(React.Fragment, null, renderField('Topic', 'topic', [{
      label: 'Mixed',
      value: 'mixed'
    }, {
      label: 'General',
      value: 'general'
    }, {
      label: 'Science',
      value: 'science'
    }, {
      label: 'History',
      value: 'history'
    }, {
      label: 'Tech',
      value: 'technology'
    }, {
      label: 'Riddles',
      value: 'riddles'
    }, {
      label: 'GK',
      value: 'gk'
    }, {
      label: 'Gau Hani Katha',
      value: 'gau_hani_katha'
    }]), renderField('Questions', 'question_count', [{
      label: 3,
      value: 3
    }, {
      label: 5,
      value: 5
    }, {
      label: 7,
      value: 7
    }, {
      label: 10,
      value: 10
    }])),
    cps: () => /*#__PURE__*/React.createElement(React.Fragment, null, renderField('Time Limit', 'time_limit', [{
      label: '5s',
      value: 5
    }, {
      label: '10s',
      value: 10
    }, {
      label: '30s',
      value: 30
    }, {
      label: '60s',
      value: 60
    }]), renderRange('Target CPS', 'target_cps', 5, 20)),
    aim3d: () => /*#__PURE__*/React.createElement(React.Fragment, null, renderRange('Target Score', 'target_score', 200, 5000, 100), renderField('Time Limit', 'time_limit', [{
      label: '15s',
      value: 15
    }, {
      label: '30s',
      value: 30
    }, {
      label: '60s',
      value: 60
    }]), renderField('Target Size', 'target_size', [{
      label: 'Small',
      value: 'small'
    }, {
      label: 'Medium',
      value: 'medium'
    }, {
      label: 'Large',
      value: 'large'
    }]), renderField('Target Speed', 'target_speed', [{
      label: 'Slow',
      value: 'slow'
    }, {
      label: 'Normal',
      value: 'normal'
    }, {
      label: 'Fast',
      value: 'fast'
    }])),
    reaction: () => /*#__PURE__*/React.createElement(React.Fragment, null, renderRange('Target Avg (ms)', 'target_avg', 100, 500, 10), renderField('Attempts', 'attempts', [{
      label: 3,
      value: 3
    }, {
      label: 5,
      value: 5
    }, {
      label: 10,
      value: 10
    }])),
    memory: () => /*#__PURE__*/React.createElement(React.Fragment, null, renderRange('Target Level', 'target_level', 3, 15), renderField('Grid Size', 'grid_size', [{
      label: '2×2',
      value: 2
    }, {
      label: '3×3',
      value: 3
    }, {
      label: '4×4',
      value: 4
    }])),
    runner: () => /*#__PURE__*/React.createElement(React.Fragment, null, renderRange('Target Score', 'target_score', 2000, 50000, 500), renderField('Time Limit', 'time_limit', [{
      label: '30s',
      value: 30
    }, {
      label: '60s',
      value: 60
    }, {
      label: '90s',
      value: 90
    }, {
      label: '120s',
      value: 120
    }, {
      label: '180s',
      value: 180
    }]), renderField('Lives', 'lives', [{
      label: 1,
      value: 1
    }, {
      label: 2,
      value: 2
    }, {
      label: 3,
      value: 3
    }, {
      label: 4,
      value: 4
    }, {
      label: 5,
      value: 5
    }]), renderField('Difficulty', 'difficulty', [{
      label: 'Easy',
      value: 'easy'
    }, {
      label: 'Normal',
      value: 'normal'
    }, {
      label: 'Hard',
      value: 'hard'
    }])),
    tictactoe: () => /*#__PURE__*/React.createElement(React.Fragment, null, renderField('Target Wins', 'target_wins', [{
      label: 1,
      value: 1
    }, {
      label: 2,
      value: 2
    }, {
      label: 3,
      value: 3
    }, {
      label: 4,
      value: 4
    }, {
      label: 5,
      value: 5
    }]), renderField('Grid Size', 'grid_size', [{
      label: '3×3',
      value: 3
    }, {
      label: '4×4',
      value: 4
    }, {
      label: '5×5',
      value: 5
    }]), renderField('Difficulty', 'difficulty', [{
      label: 'Easy',
      value: 'easy'
    }, {
      label: 'Medium',
      value: 'medium'
    }, {
      label: 'Hard',
      value: 'hard'
    }])),
    coding: () => /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: '.7rem',
        color: 'rgba(0,0,0,0.4)',
        marginBottom: 6
      }
    }, "Difficulty"), renderField('Difficulty', 'difficulty', [{
      label: 'Easy',
      value: 'easy'
    }, {
      label: 'Medium',
      value: 'medium'
    }, {
      label: 'Hard',
      value: 'hard'
    }]))
  };
  return /*#__PURE__*/React.createElement("div", {
    className: `settings-panel${!isCreator ? ' read-only' : ''}`
  }, /*#__PURE__*/React.createElement("div", {
    className: "settings-title"
  }, isCreator ? /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("i", {
    className: "fas fa-sliders-h"
  }), " Customize Challenge") : /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("i", {
    className: "fas fa-eye"
  }), " Challenge Settings")), settingsUI[challengeType] ? settingsUI[challengeType]() : /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: '.75rem',
      color: 'rgba(0,0,0,0.2)'
    }
  }, "No settings available"));
}
function shareResult(gameOver, isWinner, xp, coins, challengeType, opponent, phrase, myScore, oppScore, scoreUnit, mySecond, oppSecond, secondUnit) {
  if (!phrase) {
    var winPhrases = ['Leveling up!', 'On fire!', 'Unstoppable!', 'Peak performance!', 'Dominating!', 'Crushed it!', 'In the zone!', 'New record!', 'Taking names!', 'Flawless victory!', 'Champion mode!', 'Maximum effort!'];
    var losePhrases = ['Better luck next time!', 'Close one!', 'Next time!', 'Almost had it!', 'Good fight!', 'Keep grinding!', 'Learning every day!', 'The comeback is real!', 'Rising stronger!', 'On to the next one!', 'So close!', 'Great effort!'];
    var seed = ((gameOver.room_code || '').length + (gameOver.winner_id || 0) + (isWinner ? 50 : 0)) % (isWinner ? winPhrases : losePhrases).length;
    phrase = isWinner ? winPhrases[seed] : losePhrases[seed];
  }
  challengeType = challengeType || gameOver.challenge_type || 'challenge';
  var oppName = opponent?.display_name || opponent?.username || 'Opponent';
  var scoreStr = (myScore || '') + ' ' + (scoreUnit || '');
  var title = isWinner ? 'Victory in ' + challengeType + '! @' + oppName : 'Defeat in ' + challengeType + ' vs @' + oppName;
  var desc = isWinner ? 'Defeated ' + oppName + ' in ' + challengeType + ' — ' + scoreStr + '! ' + phrase : 'Lost to ' + oppName + ' in ' + challengeType + ' — ' + scoreStr + '. ' + phrase;
  var formData = new FormData();
  formData.append('title', title);
  formData.append('category', 'gaming');
  formData.append('description', desc);
  formData.append('proof_text', challengeType.toUpperCase() + ' | ' + scoreStr + ' | ' + (isWinner ? 'Victory' : 'Defeat') + ' | ' + phrase + ' | Opponent: ' + oppName);
  fetch('/social/create/', {
    method: 'POST',
    body: formData
  }).then(function (r) {
    return r.json();
  }).then(function (d) {
    if (d.post_id) {
      showToast('Result shared to your feed!');
    } else {
      showToast(d.error || 'Failed to share');
    }
  }).catch(function () {
    showToast('Failed to share result');
  });
}
function shareWithScreenshot(gameOver, isWinner, xp, coins, challengeType, opponent, phrase, myScore, oppScore, scoreUnit, mySecond, oppSecond, secondUnit) {
  if (typeof html2canvas === 'undefined') {
    shareResult(gameOver, isWinner, xp, coins, challengeType, opponent, phrase, myScore, oppScore, scoreUnit, mySecond, oppSecond, secondUnit);
    return;
  }
  var box = document.getElementById('resultBox');
  if (!box) {
    shareResult(gameOver, isWinner, xp, coins, challengeType, opponent, phrase, myScore, oppScore, scoreUnit, mySecond, oppSecond, secondUnit);
    return;
  }
  challengeType = challengeType || gameOver.challenge_type || 'challenge';
  var btn = document.getElementById('shareBtn');
  if (btn) btn.disabled = true;
  showToast('Preparing screenshot...');
  function doCapture() {
    box.style.overflow = 'visible';
    var allAnims = box.querySelectorAll('*');
    for (var i = 0; i < allAnims.length; i++) {
      allAnims[i].style.animation = 'none';
      allAnims[i].style.opacity = '1';
      allAnims[i].style.transform = 'none';
    }
    html2canvas(box, {
      scale: 2,
      backgroundColor: '#ffffff',
      allowTaint: true,
      useCORS: false,
      logging: false,
      imageTimeout: 5000
    }).then(function (canvas) {
      canvas.toBlob(function (blob) {
        var formData = new FormData();
        var oppName = opponent?.display_name || opponent?.username || 'Opponent';
        var scoreStr = myScore + ' ' + scoreUnit;
        var title = isWinner ? 'Victory in ' + challengeType + '! @' + oppName : 'Defeat in ' + challengeType + ' vs @' + oppName;
        var desc = isWinner ? 'Defeated ' + oppName + ' in ' + challengeType + ' — ' + scoreStr + '! ' + phrase : 'Lost to ' + oppName + ' in ' + challengeType + ' — ' + scoreStr + '. ' + phrase;
        formData.append('title', title);
        formData.append('category', 'gaming');
        formData.append('description', desc);
        formData.append('proof_text', challengeType.toUpperCase() + ' | ' + scoreStr + ' | ' + (isWinner ? 'Victory' : 'Defeat') + ' | ' + phrase + ' | Opponent: ' + oppName);
        formData.append('proof_image', blob, 'result.png');
        fetch('/social/create/', {
          method: 'POST',
          body: formData
        }).then(function (r) {
          return r.json();
        }).then(function (d) {
          if (d.post_id) {
            showToast('Shared with screenshot! Opponent tagged.');
          } else {
            shareResult(gameOver, isWinner, xp, coins, challengeType, opponent, phrase, myScore, oppScore, scoreUnit, mySecond, oppSecond, secondUnit);
          }
        }).catch(function () {
          shareResult(gameOver, isWinner, xp, coins, challengeType, opponent, phrase, myScore, oppScore, scoreUnit, mySecond, oppSecond, secondUnit);
        }).finally(function () {
          if (btn) btn.disabled = false;
        });
      }, 'image/png');
    }).catch(function () {
      shareResult(gameOver, isWinner, xp, coins, challengeType, opponent, phrase, myScore, oppScore, scoreUnit, mySecond, oppSecond, secondUnit);
    });
  }
  setTimeout(doCapture, 1200);
}
function showToast(msg) {
  const t = document.createElement('div');
  t.style.cssText = 'position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:rgba(0,0,0,0.55);color:#fff;padding:10px 20px;border-radius:10px;font-size:.8rem;z-index:9999;transition:all .3s';
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => {
    t.style.opacity = '0';
    setTimeout(() => t.remove(), 300);
  }, 2500);
}
function getDefaultSettings(type) {
  const defaults = {
    typing: {
      duration: 30,
      target_wpm: 40
    },
    quiz: {
      topic: 'mixed',
      question_count: 5
    },
    cps: {
      time_limit: 10,
      target_cps: 8
    },
    aim3d: {
      target_score: 1000,
      time_limit: 30,
      target_size: 'medium',
      target_speed: 'normal'
    },
    reaction: {
      target_avg: 200,
      attempts: 5
    },
    memory: {
      target_level: 5,
      grid_size: 3
    },
    runner: {
      target_score: 5000,
      time_limit: 60,
      lives: 3,
      difficulty: 'normal'
    },
    tictactoe: {
      target_wins: 2,
      grid_size: 3,
      difficulty: 'medium'
    },
    coding: {
      difficulty: 'easy'
    }
  };
  return defaults[type] || {};
}

// ── COMPONENT: MultiplayerRoom ──
function MultiplayerRoom({
  user,
  roomCode: initialCode
}) {
  const [view, setView] = useState(initialCode ? 'loading' : 'lobby');
  const [roomCode, setRoomCode] = useState('');
  const [joinCode, setJoinCode] = useState('');
  const [challengeType, setChallengeType] = useState('typing');
  const [challenge, setChallenge] = useState(null);
  const [gameChallengeType, setGameChallengeType] = useState('typing');
  const [countdown, setCountdown] = useState(null);
  const [gameOver, setGameOver] = useState(null);
  const [dcBanner, setDcBanner] = useState(false);
  const [loading, setLoading] = useState(false);
  const [gamePlayers, setGamePlayers] = useState([]);
  const [lastOpponentProgress, setLastOpponentProgress] = useState(null);
  const [lastSelfProgress, setLastSelfProgress] = useState(null);
  const [customSettings, setCustomSettings] = useState(null);
  const [settingsVersion, setSettingsVersion] = useState(0);
  const [pendingSettings, setPendingSettings] = useState(null);
  const [showInvitePopup, setShowInvitePopup] = useState(false);
  const [inviteFriends, setInviteFriends] = useState([]);
  const [inviteLoading, setInviteLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [animMyScore, setAnimMyScore] = useState(0);
  const [animOppScore, setAnimOppScore] = useState(0);
  const [animShowChart, setAnimShowChart] = useState(false);
  useEffect(() => {
    if (!gameOver) return;
    setAnimMyScore(0);
    setAnimOppScore(0);
    setAnimShowChart(false);
    const isQuiz = gameChallengeType === 'quiz';
    const isCPS = gameChallengeType === 'cps';
    const isReaction = gameChallengeType === 'reaction';
    const isMemory = gameChallengeType === 'memory';
    const isAim3d = gameChallengeType === 'aim3d';
    const isRunner = gameChallengeType === 'runner';
    const isTictactoe = gameChallengeType === 'tictactoe';
    const isCoding = gameChallengeType === 'coding';
    var gameAllR = gameOver?.all_results || {};
    var gameSr = gameAllR[String(user.id)] || gameOver?.self_result || {};
    var rawMy = Number(lastSelfProgress?.cps) || Number(gameSr.cps) || 0;
    var myScore = isCoding ? Number(gameSr.solved) || 0 : isQuiz ? Number(lastSelfProgress?.score) || Number(gameSr.score) || 0 : isCPS ? Math.round(rawMy * 10) / 10 : isReaction ? Number(lastSelfProgress?.best) || Number(lastSelfProgress?.best_time) || Number(gameSr.best) || Number(gameSr.best_time) || 0 : isMemory ? Number(lastSelfProgress?.level) || Number(lastSelfProgress?.current_level) || Number(gameSr.level) || Number(gameSr.current_level) || 0 : isAim3d ? Number(lastSelfProgress?.current_score) || Number(lastSelfProgress?.score) || Number(gameSr.current_score) || Number(gameSr.score) || 0 : isRunner ? Number(lastSelfProgress?.current_score) || Number(lastSelfProgress?.score) || Number(gameSr.current_score) || Number(gameSr.score) || 0 : isTictactoe ? Number(lastSelfProgress?.wins) || Number(gameSr.wins) || 0 : Number(lastSelfProgress?.wpm) || Number(gameSr.wpm) || 0;
    var myAvg = isReaction ? Number(lastSelfProgress?.avg) || Number(lastSelfProgress?.avg_time) || Number(gameSr.avg) || Number(gameSr.avg_time) || 0 : 0;
    var myTarget = myScore;
    var rawOpp = 0;
    var oppTarget = 0;
    var oppAvg = 0;
    if (lastOpponentProgress) {
      const oppProgress = Object.values(lastOpponentProgress)[0] || {};
      var oppId = Object.keys(lastOpponentProgress)[0];
      var gameOr = oppId && gameAllR[oppId] || gameOver?.opponent_result || {};
      rawOpp = Number(oppProgress.cps) || Number(gameOr.cps) || 0;
      var oppScore = isCoding ? Number(gameOr.solved) || 0 : isQuiz ? Number(oppProgress.score) || Number(gameOr.score) || 0 : isCPS ? Math.round(rawOpp * 10) / 10 : isReaction ? Number(oppProgress.best) || Number(oppProgress.best_time) || Number(gameOr.best) || Number(gameOr.best_time) || 0 : isMemory ? Number(oppProgress.level) || Number(oppProgress.current_level) || Number(gameOr.level) || Number(gameOr.current_level) || 0 : isAim3d ? Number(oppProgress.current_score) || Number(oppProgress.score) || Number(gameOr.current_score) || Number(gameOr.score) || 0 : isRunner ? Number(oppProgress.current_score) || Number(oppProgress.score) || Number(gameOr.current_score) || Number(gameOr.score) || 0 : isTictactoe ? Number(oppProgress.wins) || Number(gameOr.wins) || 0 : Number(oppProgress.wpm) || Number(gameOr.wpm) || 0;
      oppAvg = isReaction ? Number(oppProgress.avg) || Number(oppProgress.avg_time) || Number(gameOr.avg) || Number(gameOr.avg_time) || 0 : 0;
      oppTarget = oppScore;
    } else if (gameOver?.all_results) {
      var oppId2 = Object.keys(gameAllR).find(function (k) {
        return k !== String(user.id);
      });
      if (oppId2) {
        var gameOr2 = gameAllR[oppId2] || {};
        var oppRaw2 = Number(gameOr2.cps) || 0;
        var oppScore2 = isCoding ? Number(gameOr2.solved) || 0 : isQuiz ? Number(gameOr2.score) || 0 : isCPS ? Math.round(oppRaw2 * 10) / 10 : isReaction ? Number(gameOr2.best) || Number(gameOr2.best_time) || 0 : isMemory ? Number(gameOr2.level) || Number(gameOr2.current_level) || 0 : isAim3d ? Number(gameOr2.current_score) || Number(gameOr2.score) || 0 : isRunner ? Number(gameOr2.current_score) || Number(gameOr2.score) || 0 : isTictactoe ? Number(gameOr2.wins) || 0 : Number(gameOr2.wpm) || 0;
        oppTarget = oppScore2;
      }
    }
    var myStep = Math.max(1, Math.ceil(myTarget / 50));
    var oppStep = Math.max(1, Math.ceil(oppTarget / 60));
    var myTimer = setInterval(function () {
      setAnimMyScore(function (p) {
        var n = p + myStep;
        return n >= myTarget ? (clearInterval(myTimer), myTarget) : n;
      });
    }, 16);
    var oppTimer = setInterval(function () {
      setAnimOppScore(function (p) {
        var n = p + oppStep;
        return n >= oppTarget ? (clearInterval(oppTimer), oppTarget) : n;
      });
    }, 16);
    var chartTimer = setTimeout(function () {
      setAnimShowChart(true);
    }, 600);
    return function () {
      clearInterval(myTimer);
      clearInterval(oppTimer);
      clearTimeout(chartTimer);
    };
  }, [gameOver, gameChallengeType, lastSelfProgress, lastOpponentProgress]);
  useEffect(() => {
    if (!initialCode) return;
    (async () => {
      try {
        const res = await fetch('/multiplayer/join/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRF()
          },
          body: JSON.stringify({
            room_code: initialCode
          })
        });
        const data = await res.json();
        if (data.room_code) {
          setRoomCode(data.room_code);
          setView('room-lobby');
          setChallengeType(data.room && data.room.challenge_type || 'typing');
          if (data.room && data.room.custom_settings) {
            setCustomSettings(data.room.custom_settings);
          }
        } else {
          alert(data.error || 'Failed to join room');
          setView('lobby');
        }
      } catch (e) {
        alert('Network error joining room');
        setView('lobby');
      }
    })();
  }, [initialCode]);
  const handleWSMessage = useCallback(data => {
    if (data.type === 'countdown') {
      if (data.count === 0) {
        setCountdown('GO!');
        setTimeout(() => setCountdown(null), 600);
      } else {
        setCountdown(data.count);
      }
    } else if (data.type === 'challenge_start') {
      setChallenge(data.challenge);
      setGameChallengeType(data.challenge_type || 'typing');
      setGamePlayers(data.players || []);
      setView('game');
    } else if (data.type === 'opponent_progress') {
      if (gameOver) return;
      setLastOpponentProgress(prev => ({
        ...(prev || {}),
        [data.from_user_id]: data.progress
      }));
    } else if (data.type === 'game_over') {
      if (data.self_result && Object.keys(data.self_result).length > 0) {
        setLastSelfProgress(prev => ({
          ...(prev || {}),
          ...data.self_result
        }));
      }
      if (data.opponent_result && Object.keys(data.opponent_result).length > 0) {
        var oppId = data.opponent_result.user_id;
        if (oppId) {
          setLastOpponentProgress(prev => ({
            ...(prev || {}),
            [oppId]: data.opponent_result
          }));
        }
      }
      if (data.all_results && user) {
        var myId = String(user.id);
        Object.entries(data.all_results).forEach(function (entry) {
          var rid = entry[0],
            rdata = entry[1];
          if (rid !== myId && rdata) {
            var uid = rdata.user_id || Number(rid);
            setLastOpponentProgress(prev => ({
              ...(prev || {}),
              [uid]: rdata
            }));
          }
        });
      }
      setGameOver(data);
    } else if (data.type === 'room_reset') {
      setGameOver(null);
      setChallenge(null);
      setView('room-lobby');
      setChallengeType(data.challenge_type || 'typing');
      setCustomSettings(data.custom_settings || null);
      setGameChallengeType(null);
    } else if (data.type === 'player_update') {
      if (data.status === 'finished' && !gameOver) {
        setDcBanner(true);
      }
      if (data.players) {
        const allDisconnected = data.players.every(p => !p.connected);
        if (allDisconnected && data.players.length >= 2) {
          setDcBanner(true);
        }
      }
    } else if (data.type === 'typing_verify_result' && !gameOver) {
      if (data.status === 'error') {
        setGameOver({
          won: false,
          reason: 'Screenshot error: ' + (data.message || ''),
          xp: 0,
          coins: 0
        });
      }
    } else if (data.type === 'settings_update') {
      setCustomSettings(data.settings || null);
      setSettingsVersion(v => v + 1);
    } else if (data.type === 'challenge_type_update') {
      setChallengeType(data.challenge_type || 'typing');
      setCustomSettings(null);
    } else if (data.type === 'code_result') {
      // forward to coding challenge component via window event
      window.dispatchEvent(new CustomEvent('code_result', {
        detail: data
      }));
    }
  }, [gameOver]);
  const {
    sendProgress,
    sendReady,
    sendChallengeComplete,
    sendSettings,
    sendRaw,
    connectionStatus,
    roomState
  } = useMultiplayerSocket(roomCode, user.id, handleWSMessage);
  const handleSettingsChange = useCallback(settings => {
    setPendingSettings(settings);
    sendSettings(settings);
  }, [sendSettings]);
  const createRoom = async () => {
    setLoading(true);
    try {
      const res = await fetch('/multiplayer/create/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCSRF()
        },
        body: JSON.stringify({
          challenge_type: challengeType
        })
      });
      const data = await res.json();
      if (data.room_code) {
        setRoomCode(data.room_code);
        setView('room-lobby');
      } else {
        alert(data.error || 'Failed to create room');
      }
    } catch (e) {
      alert('Network error');
    }
    setLoading(false);
  };
  const joinRoom = async () => {
    if (!joinCode.trim()) return;
    setLoading(true);
    try {
      const res = await fetch('/multiplayer/join/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCSRF()
        },
        body: JSON.stringify({
          room_code: joinCode.trim()
        })
      });
      const data = await res.json();
      if (data.room_code) {
        setRoomCode(data.room_code);
        setView('room-lobby');
      } else {
        alert(data.error || 'Failed to join room');
      }
    } catch (e) {
      alert('Network error');
    }
    setLoading(false);
  };
  const handleReady = () => {
    sendReady();
  };
  const handleProgress = useCallback(progress => {
    setLastSelfProgress(prev => ({
      ...(prev || {}),
      ...progress
    }));
    sendProgress(progress);
  }, [sendProgress]);
  const handleComplete = useCallback(result => {
    setLastSelfProgress(prev => ({
      ...(prev || {}),
      ...result,
      target: result.total || result.target || prev?.target || 1
    }));
    sendChallengeComplete(result);
  }, [sendChallengeComplete]);
  const handleSubmitCode = useCallback(code => {
    sendRaw({
      type: 'submit_code',
      code: code,
      problem: challenge?.problem || ''
    });
  }, [sendRaw, challenge]);
  const handleTypingScreenshot = useCallback((screenshot, result) => {
    sendRaw({
      type: 'typing_screenshot',
      screenshot: screenshot,
      result: result
    });
  }, [sendRaw]);
  const getCSRF = () => {
    const m = document.cookie.match(/csrftoken=([\w-]+)/);
    return m ? m[1] : '';
  };

  // ── INVITE FRIENDS ──
  const openInvitePopup = async () => {
    setInviteLoading(true);
    setShowInvitePopup(true);
    try {
      const res = await fetch('/social/friends/list/');
      const data = await res.json();
      setInviteFriends(data.friends || []);
    } catch (e) {
      setInviteFriends([]);
    }
    setInviteLoading(false);
  };
  const sendFriendInvite = async friend => {
    if (!roomCode) {
      alert('No room to invite to');
      return;
    }
    try {
      const msg = '🔥 Multiplayer Arena Invite! Room: ' + roomCode + ' — Join at /multiplayer/?room=' + roomCode;
      await fetch('/chatx/send/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCSRF()
        },
        body: JSON.stringify({
          receiver_id: friend.id,
          content: msg
        })
      });
      setShowInvitePopup(false);
    } catch (e) {
      alert('Failed to send invite');
    }
  };

  // ── LOADING VIEW (auto-joining room from invite) ──
  if (view === 'loading') {
    return /*#__PURE__*/React.createElement("div", {
      className: "lobby glass",
      style: {
        textAlign: 'center',
        padding: 40
      }
    }, /*#__PURE__*/React.createElement("i", {
      className: "fas fa-spinner fa-spin",
      style: {
        fontSize: '1.5rem',
        color: '#2d7dd2',
        marginBottom: 16,
        display: 'block'
      }
    }), /*#__PURE__*/React.createElement("p", {
      style: {
        color: 'rgba(0,0,0,0.6)',
        fontSize: '.85rem'
      }
    }, "Joining arena..."));
  }

  // ── LOBBY VIEW (create/join) ──
  if (view === 'lobby') {
    return /*#__PURE__*/React.createElement("div", {
      className: "lobby glass"
    }, /*#__PURE__*/React.createElement("h1", null, /*#__PURE__*/React.createElement("i", {
      className: "fas fa-gamepad"
    }), " ChillX Arena"), /*#__PURE__*/React.createElement("p", {
      className: "sub"
    }, "Compete in real-time challenges"), /*#__PURE__*/React.createElement("div", {
      className: "tabs"
    }, /*#__PURE__*/React.createElement("button", {
      className: `tab ${view === 'lobby' ? 'active' : ''}`,
      onClick: () => {}
    }, "Create"), /*#__PURE__*/React.createElement("button", {
      className: `tab ${view === 'lobby' ? 'active' : ''}`,
      onClick: () => {}
    }, "Join")), /*#__PURE__*/React.createElement("div", {
      className: "challenge-picker"
    }, [{
      id: 'typing',
      icon: 'fa-keyboard',
      label: 'Typing'
    }, {
      id: 'quiz',
      icon: 'fa-question-circle',
      label: 'Quiz'
    }, {
      id: 'cps',
      icon: 'fa-mouse-pointer',
      label: 'CPS'
    }, {
      id: 'aim3d',
      icon: 'fa-crosshairs',
      label: 'Aim 3D'
    }, {
      id: 'reaction',
      icon: 'fa-bolt',
      label: 'Reaction'
    }, {
      id: 'memory',
      icon: 'fa-brain',
      label: 'Memory'
    }, {
      id: 'runner',
      icon: 'fa-running',
      label: 'Runner'
    }, {
      id: 'tictactoe',
      icon: 'fa-hashtag',
      label: 'TicTacToe'
    }, {
      id: 'coding',
      icon: 'fa-code',
      label: 'Coding'
    }].map(t => /*#__PURE__*/React.createElement("button", {
      key: t.id,
      className: challengeType === t.id ? 'active' : '',
      onClick: () => setChallengeType(t.id)
    }, /*#__PURE__*/React.createElement("i", {
      className: `fas ${t.icon}`
    }), " ", t.label))), /*#__PURE__*/React.createElement("input", {
      placeholder: "Enter room code...",
      value: joinCode,
      onChange: e => setJoinCode(e.target.value.toUpperCase()),
      maxLength: 6,
      style: {
        marginBottom: 8
      }
    }), /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        gap: 8
      }
    }, /*#__PURE__*/React.createElement("button", {
      className: "create-btn",
      onClick: createRoom,
      disabled: loading,
      style: {
        flex: 1
      }
    }, loading ? /*#__PURE__*/React.createElement("i", {
      className: "fas fa-spinner fa-spin"
    }) : /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("i", {
      className: "fas fa-plus"
    }), " Create Room")), /*#__PURE__*/React.createElement("button", {
      className: "join-btn",
      onClick: joinRoom,
      disabled: loading || !joinCode.trim(),
      style: {
        flex: 1
      }
    }, loading ? /*#__PURE__*/React.createElement("i", {
      className: "fas fa-spinner fa-spin"
    }) : /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("i", {
      className: "fas fa-sign-in-alt"
    }), " Join"))));
  }

  // ── ROOM LOBBY ──
  if (view === 'room-lobby' && !challenge) {
    const players = roomState?.players || [];
    const myPlayer = players.find(p => p.user_id === user.id);
    const allReady = players.length >= 2 && players.every(p => p.is_ready);
    const hostConnected = connectionStatus === 'connected';
    return /*#__PURE__*/React.createElement("div", {
      className: "room-lobby glass"
    }, /*#__PURE__*/React.createElement("div", {
      className: "code-label"
    }, "Room Code"), /*#__PURE__*/React.createElement("div", {
      className: "room-code"
    }, roomCode), /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: 11,
        color: 'rgba(0,0,0,0.35)',
        marginBottom: 6
      }
    }, "Status: ", connectionStatus === 'connected' ? /*#__PURE__*/React.createElement("span", {
      style: {
        color: '#2d7dd2'
      }
    }, "Connected ", /*#__PURE__*/React.createElement("i", {
      className: "fas fa-circle",
      style: {
        fontSize: 6
      }
    })) : /*#__PURE__*/React.createElement("span", {
      style: {
        color: '#ff4757'
      }
    }, "Connecting...")), /*#__PURE__*/React.createElement("div", {
      className: "players-row"
    }, players.map((p, i) => /*#__PURE__*/React.createElement(React.Fragment, {
      key: p.user_id
    }, i > 0 && /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        alignItems: 'center',
        fontFamily: 'Orbitron',
        fontSize: '1rem',
        color: 'rgba(0,0,0,0.15)',
        letterSpacing: 1
      }
    }, "VS"), /*#__PURE__*/React.createElement("div", {
      className: "player-slot"
    }, /*#__PURE__*/React.createElement("div", {
      className: "avatar"
    }, p.avatar ? /*#__PURE__*/React.createElement("img", {
      src: p.avatar
    }) : /*#__PURE__*/React.createElement("i", {
      className: "fas fa-user"
    })), /*#__PURE__*/React.createElement("div", {
      className: "pname"
    }, p.display_name), /*#__PURE__*/React.createElement("div", {
      className: "prank"
    }, p.rank, " · Lv", p.level), /*#__PURE__*/React.createElement("div", {
      className: `pstatus ${p.is_ready ? 'ready' : !p.connected ? 'disconnected' : 'waiting'}`
    }, !p.connected ? 'Disconnected' : p.is_ready ? '✓ Ready' : 'Waiting...'), p.user_id === user.id && /*#__PURE__*/React.createElement("div", {
      className: "you-badge"
    }, "YOU")))), players.length < 2 && /*#__PURE__*/React.createElement(React.Fragment, null, players.length > 0 && /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        alignItems: 'center',
        fontFamily: 'Orbitron',
        fontSize: '1rem',
        color: 'rgba(0,0,0,0.15)',
        letterSpacing: 1
      }
    }, "VS"), /*#__PURE__*/React.createElement("div", {
      className: "player-slot empty"
    }, /*#__PURE__*/React.createElement("div", {
      className: "avatar"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fas fa-user-plus"
    })), /*#__PURE__*/React.createElement("div", {
      className: "pname",
      style: {
        color: 'rgba(0,0,0,0.2)'
      }
    }, "Waiting...")))), players.length >= 2 && !allReady && /*#__PURE__*/React.createElement("div", {
      style: {
        marginBottom: 4,
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        justifyContent: 'center'
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: 12,
        color: 'rgba(0,0,0,0.4)'
      }
    }, "Challenge: ", /*#__PURE__*/React.createElement("span", {
      style: {
        color: '#2d7dd2',
        fontWeight: 600,
        textTransform: 'uppercase'
      }
    }, challengeType)), players[0]?.user_id === user.id && /*#__PURE__*/React.createElement("button", {
      className: "ready-btn",
      style: {
        background: 'linear-gradient(180deg,#2d7dd2,#1a5276)',
        padding: '4px 12px',
        fontSize: 12
      },
      onClick: () => setShowSettings(true)
    }, /*#__PURE__*/React.createElement("i", {
      className: "fas fa-cog"
    }), " Settings")), showSettings && players[0]?.user_id === user.id && /*#__PURE__*/React.createElement("div", {
      style: {
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(0,0,0,0.55)',
        zIndex: 10000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      },
      onClick: e => {
        if (e.target === e.currentTarget) setShowSettings(false);
      }
    }, /*#__PURE__*/React.createElement("div", {
      className: "glass",
      style: {
        width: '90%',
        maxWidth: 380,
        padding: 16,
        borderRadius: 14,
        maxHeight: '80vh',
        overflow: 'auto'
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 10
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        fontFamily: 'Orbitron',
        fontSize: 13,
        fontWeight: 700,
        color: '#2d7dd2'
      }
    }, "Game Settings"), /*#__PURE__*/React.createElement("button", {
      style: {
        background: 'none',
        border: 'none',
        color: 'rgba(0,0,0,0.4)',
        fontSize: 18,
        cursor: 'pointer'
      },
      onClick: () => setShowSettings(false)
    }, /*#__PURE__*/React.createElement("i", {
      className: "fas fa-times"
    }))), /*#__PURE__*/React.createElement("div", {
      className: "challenge-picker",
      style: {
        marginBottom: 10
      }
    }, [{
      id: 'typing',
      icon: 'fa-keyboard',
      label: 'Typing'
    }, {
      id: 'quiz',
      icon: 'fa-question-circle',
      label: 'Quiz'
    }, {
      id: 'cps',
      icon: 'fa-mouse-pointer',
      label: 'CPS'
    }, {
      id: 'aim3d',
      icon: 'fa-crosshairs',
      label: 'Aim 3D'
    }, {
      id: 'reaction',
      icon: 'fa-bolt',
      label: 'Reaction'
    }, {
      id: 'memory',
      icon: 'fa-brain',
      label: 'Memory'
    }, {
      id: 'runner',
      icon: 'fa-running',
      label: 'Runner'
    }, {
      id: 'tictactoe',
      icon: 'fa-hashtag',
      label: 'TicTacToe'
    }, {
      id: 'coding',
      icon: 'fa-code',
      label: 'Coding'
    }].map(t => /*#__PURE__*/React.createElement("button", {
      key: t.id,
      className: challengeType === t.id ? 'active' : '',
      onClick: () => {
        setChallengeType(t.id);
        setCustomSettings(null);
        sendRaw({
          type: 'update_challenge_type',
          challenge_type: t.id
        });
      }
    }, /*#__PURE__*/React.createElement("i", {
      className: `fas ${t.icon}`
    }), " ", t.label))), /*#__PURE__*/React.createElement(ChallengeSettings, {
      challengeType: challengeType,
      currentSettings: customSettings,
      onChange: handleSettingsChange,
      isCreator: true
    }))), players.length >= 2 && !allReady && /*#__PURE__*/React.createElement(ChallengeSettings, {
      challengeType: challengeType,
      currentSettings: customSettings,
      onChange: handleSettingsChange,
      isCreator: players[0]?.user_id === user.id
    }), allReady && /*#__PURE__*/React.createElement("div", {
      className: "waiting-msg"
    }, /*#__PURE__*/React.createElement("span", null, "Starting game"), /*#__PURE__*/React.createElement("div", {
      className: "dots"
    }, /*#__PURE__*/React.createElement("span", null), /*#__PURE__*/React.createElement("span", null), /*#__PURE__*/React.createElement("span", null))), myPlayer && !myPlayer.is_ready && players.length >= 2 && /*#__PURE__*/React.createElement("button", {
      className: "ready-btn",
      onClick: handleReady,
      disabled: !hostConnected
    }, /*#__PURE__*/React.createElement("i", {
      className: "fas fa-check-circle"
    }), " Ready"), myPlayer && myPlayer.is_ready && /*#__PURE__*/React.createElement("button", {
      className: "ready-btn ready",
      disabled: true
    }, /*#__PURE__*/React.createElement("i", {
      className: "fas fa-check"
    }), " Ready!"), players.length < 8 && /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("div", {
      className: "waiting-msg"
    }, /*#__PURE__*/React.createElement("i", {
      className: "fas fa-hourglass-half"
    }), " Waiting for players to join (", players.length, "/8)", /*#__PURE__*/React.createElement("div", {
      className: "dots"
    }, /*#__PURE__*/React.createElement("span", null), /*#__PURE__*/React.createElement("span", null), /*#__PURE__*/React.createElement("span", null))), /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        gap: 6,
        justifyContent: 'center',
        flexWrap: 'wrap',
        marginTop: 6
      }
    }, /*#__PURE__*/React.createElement("button", {
      className: "ready-btn",
      style: {
        background: 'linear-gradient(180deg,#2d7dd2,#1a5276)'
      },
      onClick: openInvitePopup
    }, /*#__PURE__*/React.createElement("i", {
      className: "fas fa-user-plus"
    }), " Invite Friend"), /*#__PURE__*/React.createElement("button", {
      className: "ready-btn",
      style: {
        background: 'linear-gradient(180deg,#2d7dd2,#1a5276)'
      },
      onClick: () => {
        const link = window.location.origin + '/multiplayer/?room=' + roomCode;
        navigator.clipboard.writeText(link).then(() => {
          setCopied(true);
          setTimeout(() => setCopied(false), 2000);
        });
      }
    }, /*#__PURE__*/React.createElement("i", {
      className: `fas ${copied ? 'fa-check' : 'fa-link'}`
    }), " ", copied ? 'Copied!' : 'Copy Invite Link'))), showInvitePopup && /*#__PURE__*/React.createElement("div", {
      style: {
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(0,0,0,0.55)',
        zIndex: 10000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      },
      onClick: e => {
        if (e.target === e.currentTarget) setShowInvitePopup(false);
      }
    }, /*#__PURE__*/React.createElement("div", {
      className: "glass",
      style: {
        width: '90%',
        maxWidth: 340,
        padding: 16,
        borderRadius: 14,
        maxHeight: '80vh',
        overflow: 'auto'
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        fontSize: 14,
        fontWeight: 700,
        color: '#2d7dd2',
        marginBottom: 10,
        display: 'flex',
        alignItems: 'center',
        gap: 6
      }
    }, /*#__PURE__*/React.createElement("i", {
      className: "fas fa-user-friends"
    }), " Invite a Friend"), inviteLoading ? /*#__PURE__*/React.createElement("div", {
      style: {
        textAlign: 'center',
        padding: 20,
        color: 'rgba(0,0,0,0.4)'
      }
    }, "Loading friends...") : inviteFriends.length === 0 ? /*#__PURE__*/React.createElement("div", {
      style: {
        textAlign: 'center',
        padding: 20,
        color: 'rgba(0,0,0,0.4)'
      }
    }, "No friends found. Add friends from your social page!") : /*#__PURE__*/React.createElement("div", {
      style: {
        display: 'flex',
        flexDirection: 'column',
        gap: 6
      }
    }, inviteFriends.map(f => /*#__PURE__*/React.createElement("button", {
      key: f.id,
      onClick: () => sendFriendInvite(f),
      style: {
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        padding: '8px 12px',
        border: '1px solid rgba(45,125,210,0.08)',
        borderRadius: 10,
        background: 'var(--surface)',
        color: 'var(--text)',
        cursor: 'pointer',
        fontSize: 13,
        fontFamily: 'inherit',
        textAlign: 'left',
        transition: 'all .15s'
      },
      onMouseEnter: e => e.currentTarget.style.borderColor = 'rgba(45,125,210,0.3)',
      onMouseLeave: e => e.currentTarget.style.borderColor = 'rgba(45,125,210,0.08)'
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        width: 28,
        height: 28,
        borderRadius: '50%',
        background: 'rgba(45,125,210,0.15)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontWeight: 700,
        fontSize: 12,
        color: '#2d7dd2',
        overflow: 'hidden'
      }
    }, f.has_avatar ? /*#__PURE__*/React.createElement("img", {
      src: '/api/shop/avatar/?user_id=' + f.id,
      style: {
        width: '100%',
        height: '100%',
        objectFit: 'cover'
      }
    }) : (f.username?.[0] || '?').toUpperCase()), /*#__PURE__*/React.createElement("span", {
      style: {
        fontWeight: 600
      }
    }, f.username)))), /*#__PURE__*/React.createElement("button", {
      onClick: () => setShowInvitePopup(false),
      style: {
        width: '100%',
        marginTop: 10,
        padding: '8px',
        border: '1px solid rgba(45,125,210,0.1)',
        borderRadius: 10,
        background: 'transparent',
        color: 'rgba(0,0,0,0.5)',
        cursor: 'pointer',
        fontSize: 12,
        fontFamily: 'inherit'
      }
    }, "Cancel"))));
  }

  // ── COUNTDOWN OVERLAY ──
  if (countdown) {
    return /*#__PURE__*/React.createElement("div", {
      className: "countdown-overlay"
    }, /*#__PURE__*/React.createElement("div", {
      className: `countdown-num${countdown === 'GO!' ? ' go' : ''}`
    }, countdown === 'GO!' ? '▶' : countdown));
  }
  const allPlayers = gamePlayers.length > 0 ? gamePlayers : roomState?.players || [];
  const myName = allPlayers.find(p => p.user_id === user.id)?.display_name || user.display_name;

  // ── GAME OVER OVERLAY ──
  if (gameOver) {
    const isWinner = gameOver.winner_id === user.id;
    const xp = isWinner ? gameOver.xp_winner || 0 : gameOver.xp_loser || 0;
    const coins = isWinner ? gameOver.coins_winner || 0 : gameOver.coins_loser || 0;
    const isQuiz = gameChallengeType === 'quiz';
    const isCPS = gameChallengeType === 'cps';
    const isReaction = gameChallengeType === 'reaction';
    const isMemory = gameChallengeType === 'memory';
    const isAim3d = gameChallengeType === 'aim3d';
    const isRunner = gameChallengeType === 'runner';
    const isTictactoe = gameChallengeType === 'tictactoe';
    const isCoding = gameChallengeType === 'coding';
    var allR = gameOver.all_results || {};
    var myIdStr = String(user.id);
    var sr = allR[myIdStr] || gameOver.self_result || {};
    var rawCps = Number(lastSelfProgress?.cps) || Number(sr.cps) || 0;
    const displayScore1 = isCoding ? Number(sr.solved) || 0 : isQuiz ? Number(lastSelfProgress?.score) || Number(sr.score) || 0 : isCPS ? Math.round(rawCps * 10) / 10 : isReaction ? Number(lastSelfProgress?.best) || Number(lastSelfProgress?.best_time) || Number(sr.best) || Number(sr.best_time) || 0 : isMemory ? Number(lastSelfProgress?.level) || Number(lastSelfProgress?.current_level) || Number(sr.level) || Number(sr.current_level) || 0 : isAim3d ? Number(lastSelfProgress?.current_score) || Number(lastSelfProgress?.score) || Number(sr.current_score) || Number(sr.score) || 0 : isRunner ? Number(lastSelfProgress?.current_score) || Number(lastSelfProgress?.score) || Number(sr.current_score) || Number(sr.score) || 0 : isTictactoe ? Number(lastSelfProgress?.wins) || Number(sr.wins) || 0 : Number(lastSelfProgress?.wpm) || Number(sr.wpm) || 0;
    const displayPct1 = isCoding ? 0 : isReaction ? Number(sr.avg) || Number(sr.avg_time) || Number(lastSelfProgress?.avg) || Number(lastSelfProgress?.avg_time) || 0 : isCPS ? Number(sr.clicks) || Number(lastSelfProgress?.clicks) || 0 : Number(sr.accuracy) || Number(lastSelfProgress?.accuracy) || Number(sr.percent_complete) || Number(lastSelfProgress?.percent_complete) || 0;
    const opponent = allPlayers.find(p => p.user_id !== user.id);
    const oppData = lastOpponentProgress ? Object.values(lastOpponentProgress)[0] : null;
    var or = opponent ? allR[String(opponent.user_id)] || gameOver.opponent_result || {} : gameOver.opponent_result || {};
    var rawOppCps = Number(oppData?.cps) || Number(or.cps) || 0;
    const oppScore1 = isCoding ? Number(or.solved) || 0 : isQuiz ? Number(oppData?.score) || Number(or.score) || 0 : isCPS ? Math.round(rawOppCps * 10) / 10 : isReaction ? Number(oppData?.best) || Number(oppData?.best_time) || Number(or.best) || Number(or.best_time) || 0 : isMemory ? Number(oppData?.level) || Number(oppData?.current_level) || Number(or.level) || Number(or.current_level) || 0 : isAim3d ? Number(oppData?.current_score) || Number(oppData?.score) || Number(or.current_score) || Number(or.score) || 0 : isRunner ? Number(oppData?.current_score) || Number(oppData?.score) || Number(or.current_score) || Number(or.score) || 0 : isTictactoe ? Number(oppData?.wins) || Number(or.wins) || 0 : Number(oppData?.wpm) || Number(or.wpm) || 0;
    const oppPct1 = isCoding ? 0 : isReaction ? Number(or.avg) || Number(or.avg_time) || Number(oppData?.avg) || Number(oppData?.avg_time) || 0 : isCPS ? Number(or.clicks) || Number(oppData?.clicks) || 0 : Number(or.accuracy) || Number(oppData?.accuracy) || Number(or.percent_complete) || Number(oppData?.percent_complete) || 0;
    const me = allPlayers.find(p => p.user_id === user.id);
    const myAvatar = me?.avatar ? React.createElement('img', {
      src: me.avatar,
      alt: '',
      style: {
        width: '100%',
        height: '100%',
        objectFit: 'cover',
        display: 'block'
      },
      onError: function (e) {
        e.target.style.display = 'none';
      }
    }) : React.createElement('i', {
      className: 'fas fa-user'
    });
    const oppAvatar = opponent?.avatar ? React.createElement('img', {
      src: opponent.avatar,
      alt: '',
      style: {
        width: '100%',
        height: '100%',
        objectFit: 'cover',
        display: 'block'
      },
      onError: function (e) {
        e.target.style.display = 'none';
      }
    }) : React.createElement('i', {
      className: 'fas fa-user'
    });
    const theme = isWinner ? 'win' : 'lose';
    const scoreUnit = isCoding ? 'SOLVED' : isQuiz ? 'SCORE' : isCPS ? 'CPS' : isReaction ? 'MS' : isMemory ? 'LEVEL' : isAim3d ? 'SCORE' : isRunner ? 'SCORE' : isTictactoe ? 'WINS' : 'WPM';
    const pctUnit = isCoding ? '' : isReaction ? 'AVG MS' : isMemory ? 'LEVEL' : isAim3d ? '%' : isRunner ? '%' : isTictactoe ? 'WINS' : isCPS ? 'CLICKS' : 'ACC%';
    const maxScore = Math.max(displayScore1, oppScore1, 1);
    const maxPct = Math.max(displayPct1, oppPct1, 1);
    const winPhrases = ['Leveling up!', 'On fire!', 'Unstoppable!', 'Peak performance!', 'Dominating!', 'Crushed it!', 'In the zone!', 'New record!', 'Taking names!', 'Flawless victory!', 'Champion mode!', 'Maximum effort!'];
    const losePhrases = ['Better luck next time!', 'Close one!', 'Next time!', 'Almost had it!', 'Good fight!', 'Keep grinding!', 'Learning every day!', 'The comeback is real!', 'Rising stronger!', 'On to the next one!', 'So close!', 'Great effort!'];
    const phraseIdx = ((gameOver.room_code || '').length + (gameOver.winner_id || 0) + (isWinner ? 50 : 0)) % (isWinner ? winPhrases : losePhrases).length;
    const overlayPhrase = isWinner ? winPhrases[phraseIdx] : losePhrases[phraseIdx];
    return React.createElement('div', {
      className: 'game-over-overlay',
      id: 'resultOverlay'
    }, React.createElement('div', {
      className: 'game-over-box ' + theme,
      id: 'resultBox'
    }, isWinner ? React.createElement('div', null, React.createElement('div', {
      className: 'go-badge win'
    }, 'VICTORY'), React.createElement('div', {
      className: 'go-sub'
    }, 'You dominated this round!')) : React.createElement('div', null, React.createElement('div', {
      className: 'go-badge lose'
    }, 'DEFEAT'), React.createElement('div', {
      className: 'go-sub'
    }, gameOver.winner_username + ' won this round')), React.createElement('div', {
      className: 'go-score-row'
    }, React.createElement('div', {
      className: 'go-score-card left ' + (isWinner ? 'win' : 'lose')
    }, React.createElement('div', {
      className: 'sc-avatar'
    }, myAvatar), React.createElement('div', {
      className: 'sc-name'
    }, me?.display_name || 'You'), React.createElement('div', {
      className: 'sc-num'
    }, animMyScore, ' ', React.createElement('span', {
      className: 'sc-unit'
    }, scoreUnit)), React.createElement('div', {
      className: 'sc-label'
    }, isWinner ? 'Winner' : 'You')), React.createElement('div', {
      className: 'go-vs'
    }, 'VS'), React.createElement('div', {
      className: 'go-score-card right ' + (isWinner ? 'lose' : 'win')
    }, React.createElement('div', {
      className: 'sc-avatar'
    }, oppAvatar), React.createElement('div', {
      className: 'sc-name'
    }, opponent?.display_name || 'Opponent'), React.createElement('div', {
      className: 'sc-num'
    }, animOppScore, ' ', React.createElement('span', {
      className: 'sc-unit'
    }, scoreUnit)), React.createElement('div', {
      className: 'sc-label'
    }, isWinner ? 'Opponent' : 'Winner'))), animShowChart && React.createElement('div', {
      className: 'go-bar-chart',
      key: 'chart'
    }, React.createElement('div', {
      className: 'go-bar-section'
    }, React.createElement('div', {
      className: 'go-bar-header'
    }, React.createElement('span', null, scoreUnit), React.createElement('span', null, displayScore1 + ' / ' + oppScore1)), React.createElement('div', {
      className: 'go-bar-cols'
    }, React.createElement('div', {
      className: 'go-bar-col'
    }, React.createElement('div', {
      className: 'go-bar-track'
    }, React.createElement('div', {
      className: 'go-bar-fill me',
      style: {
        width: Math.min(displayScore1 / maxScore * 100, 100) + '%',
        transitionDelay: '0.1s'
      }
    }, displayScore1 > 0 ? displayScore1 : '')), React.createElement('div', {
      className: 'go-bar-label'
    }, 'You')), React.createElement('div', {
      className: 'go-bar-col'
    }, React.createElement('div', {
      className: 'go-bar-track'
    }, React.createElement('div', {
      className: 'go-bar-fill opp',
      style: {
        width: Math.min(oppScore1 / maxScore * 100, 100) + '%',
        transitionDelay: '0.25s'
      }
    }, oppScore1 > 0 ? oppScore1 : '')), React.createElement('div', {
      className: 'go-bar-label'
    }, opponent?.display_name || 'Opp')))), !isCoding && !isTictactoe && React.createElement('div', {
      className: 'go-bar-section'
    }, React.createElement('div', {
      className: 'go-bar-header'
    }, React.createElement('span', null, pctUnit), React.createElement('span', null, displayPct1 + ' / ' + oppPct1)), React.createElement('div', {
      className: 'go-bar-cols'
    }, React.createElement('div', {
      className: 'go-bar-col'
    }, React.createElement('div', {
      className: 'go-bar-track'
    }, React.createElement('div', {
      className: 'go-bar-fill me',
      style: {
        width: Math.min(displayPct1 / maxPct * 100, 100) + '%',
        transitionDelay: '0.35s'
      }
    }, displayPct1 > 0 ? displayPct1 + (isCPS || isReaction ? '' : '%') : '')), React.createElement('div', {
      className: 'go-bar-label'
    }, 'You')), React.createElement('div', {
      className: 'go-bar-col'
    }, React.createElement('div', {
      className: 'go-bar-track'
    }, React.createElement('div', {
      className: 'go-bar-fill opp',
      style: {
        width: Math.min(oppPct1 / maxPct * 100, 100) + '%',
        transitionDelay: '0.5s'
      }
    }, oppPct1 > 0 ? oppPct1 + (isCPS || isReaction ? '' : '%') : '')), React.createElement('div', {
      className: 'go-bar-label'
    }, opponent?.display_name || 'Opp'))))), React.createElement('div', {
      className: 'go-rewards'
    }, React.createElement('div', {
      className: 'rw'
    }, React.createElement('div', {
      className: 'rw-num',
      style: {
        color: '#f7c948'
      }
    }, React.createElement('i', {
      className: 'fas fa-star'
    }), ' +' + xp), React.createElement('div', {
      className: 'rw-lbl'
    }, 'XP Earned')), isWinner ? React.createElement('div', {
      className: 'rw'
    }, React.createElement('div', {
      className: 'rw-num',
      style: {
        color: '#2d7dd2'
      }
    }, React.createElement('i', {
      className: 'fas fa-coins'
    }), ' +' + coins), React.createElement('div', {
      className: 'rw-lbl'
    }, 'Coins')) : React.createElement('div', {
      className: 'rw',
      style: {
        opacity: 0.7
      }
    }, React.createElement('div', {
      className: 'rw-num',
      style: {
        color: '#a855f7',
        fontSize: '.65rem',
        fontWeight: 500,
        letterSpacing: 0
      }
    }, React.createElement('i', {
      className: 'fas fa-quote-left',
      style: {
        marginRight: 4,
        fontSize: '.5rem',
        opacity: 0.5
      }
    }), overlayPhrase), React.createElement('div', {
      className: 'rw-lbl'
    }, ''))), React.createElement('div', {
      style: {
        display: 'flex',
        gap: 8,
        justifyContent: 'center'
      }
    }, React.createElement('button', {
      className: 'go-btn ghost',
      onClick: function () {
        window.location.href = '/challenges/';
      }
    }, React.createElement('i', {
      className: 'fas fa-times'
    }), ' Leave'), React.createElement('button', {
      className: 'go-btn share',
      id: 'shareBtn',
      onClick: function () {
        shareWithScreenshot(gameOver, isWinner, xp, coins, gameChallengeType, opponent, overlayPhrase, displayScore1, oppScore1, scoreUnit, displayPct1, oppPct1, pctUnit);
      }
    }, React.createElement('i', {
      className: 'fas fa-camera'
    }), ' Share'), React.createElement('button', {
      className: 'go-btn primary',
      onClick: function () {
        sendRaw({
          type: 'reset_room'
        });
      }
    }, React.createElement('i', {
      className: 'fas fa-redo'
    }), ' Rematch'))));
  }

  // ── GAME VIEW ──
  return /*#__PURE__*/React.createElement("div", {
    className: "game-wrap"
  }, dcBanner && /*#__PURE__*/React.createElement("div", {
    className: "dc-banner"
  }, /*#__PURE__*/React.createElement("i", {
    className: "fas fa-exclamation-triangle"
  }), " Player disconnected — waiting for reconnection..."), /*#__PURE__*/React.createElement("div", {
    className: "game-body"
  }, /*#__PURE__*/React.createElement("div", {
    className: "game-main"
  }, challenge && /*#__PURE__*/React.createElement(ChallengeGame, {
    challenge: challenge,
    challengeType: gameChallengeType,
    roomCode: roomCode,
    onProgress: handleProgress,
    onComplete: handleComplete,
    onOpponentProgress: lastOpponentProgress,
    onSubmitCode: handleSubmitCode,
    onTypingScreenshot: handleTypingScreenshot,
    players: allPlayers,
    userId: user.id
  }))));
}

// ── APP ──
function App() {
  const [userData, setUserData] = useState(null);
  const [roomCode] = useState(new URLSearchParams(window.location.search).get('room') || '');
  useEffect(function () {
    var el = document.getElementById('user-data');
    if (el && el.textContent) {
      try {
        var data = JSON.parse(el.textContent);
        if (data && data.id) {
          setUserData({
            id: data.id,
            username: data.username || 'User',
            display_name: data.display_name || data.username || 'User',
            level: data.level || 1
          });
          return;
        }
      } catch (e) {
        console.error('Failed to parse user data:', e);
      }
    }
    fetch('/api/user-stats/', {
      credentials: 'include'
    }).then(function (r) {
      return r.json();
    }).then(function (data) {
      if (data && data.level !== undefined) {
        setUserData({
          id: 0,
          username: 'Player',
          display_name: 'Player',
          level: data.level
        });
      }
    }).catch(function () {});
  }, []);
  if (!userData) {
    return /*#__PURE__*/React.createElement("div", {
      style: {
        textAlign: 'center',
        color: 'rgba(0,0,0,0.35)',
        fontSize: '.9rem',
        padding: 40
      }
    }, /*#__PURE__*/React.createElement("i", {
      className: "fas fa-spinner fa-spin",
      style: {
        fontSize: '1.5rem',
        marginBottom: 12,
        display: 'block'
      }
    }), "Loading...");
  }
  return /*#__PURE__*/React.createElement(MultiplayerRoom, {
    user: userData,
    roomCode: roomCode
  });
}
function ErrorFallback() {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      textAlign: 'center',
      padding: 40,
      fontSize: '.9rem',
      color: 'rgba(0,0,0,0.5)'
    }
  }, /*#__PURE__*/React.createElement("i", {
    className: "fas fa-exclamation-triangle",
    style: {
      fontSize: '1.5rem',
      marginBottom: 12,
      display: 'block',
      color: '#ff4757'
    }
  }), /*#__PURE__*/React.createElement("p", null, "Something went wrong loading the game lobby."), /*#__PURE__*/React.createElement("button", {
    onClick: () => window.location.reload(),
    style: {
      marginTop: 12,
      padding: '8px 20px',
      border: 'none',
      borderRadius: 8,
      background: '#2d7dd2',
      color: '#fff',
      cursor: 'pointer',
      fontFamily: 'inherit'
    }
  }, "Refresh"));
}
class ErrorBoundary extends React.Component {
  constructor(p) {
    super(p);
    this.state = {
      hasError: false
    };
  }
  static getDerivedStateFromError() {
    return {
      hasError: true
    };
  }
  componentDidCatch(err, info) {
    console.error('React error:', err, info);
  }
  render() {
    return this.state.hasError ? React.createElement(ErrorFallback) : this.props.children;
  }
}
const root = createRoot(document.getElementById('root'));
root.render(React.createElement(ErrorBoundary, null, React.createElement(App)));