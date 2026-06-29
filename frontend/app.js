const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const statusEl = document.getElementById('status');
const transcriptEl = document.getElementById('transcript');

let audioCtx = null;
let ws = null;
let mediaStream = null;
let workletNode = null;
let sourceNode = null;

function setStatus(text, live = false) {
  statusEl.textContent = text;
  statusEl.classList.toggle('live', live);
}

function addItem(en, vi) {
  const div = document.createElement('div');
  div.className = 'item';
  div.innerHTML =
    `<div class="en">${escapeHtml(en)}</div>` +
    `<div class="vi">${escapeHtml(vi)}</div>`;
  transcriptEl.appendChild(div);
  transcriptEl.scrollTop = transcriptEl.scrollHeight;
}

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[c]));
}

async function start() {
  try {
    // Bat audio he thong qua chia se man hinh. Chrome yeu cau video:true,
    // nguoi dung phai tick "Share system/tab audio".
    mediaStream = await navigator.mediaDevices.getDisplayMedia({
      video: true,
      audio: true,
    });
  } catch (e) {
    setStatus('Da huy chon man hinh');
    return;
  }

  const audioTracks = mediaStream.getAudioTracks();
  if (audioTracks.length === 0) {
    alert('Khong co audio! Hay tick "Share tab/system audio" khi chon man hinh.');
    mediaStream.getTracks().forEach((t) => t.stop());
    setStatus('Thieu audio - thu lai');
    return;
  }

  // Khong can video -> tat de do ton tai nguyen.
  mediaStream.getVideoTracks().forEach((t) => t.stop());

  // Khi nguoi dung bam "Stop sharing" cua trinh duyet.
  audioTracks[0].addEventListener('ended', stop);

  // WebSocket toi backend local.
  ws = new WebSocket(`ws://${location.host}/ws`);
  ws.binaryType = 'arraybuffer';
  ws.onmessage = (ev) => {
    const { en, vi } = JSON.parse(ev.data);
    addItem(en, vi);
  };
  ws.onclose = () => setStatus('Mat ket noi backend');

  await new Promise((res) => (ws.onopen = res));

  // AudioContext o 16kHz -> trinh duyet tu resample audio he thong ve 16kHz.
  audioCtx = new AudioContext({ sampleRate: 16000 });
  await audioCtx.audioWorklet.addModule('audio-processor.js');

  sourceNode = audioCtx.createMediaStreamSource(mediaStream);
  workletNode = new AudioWorkletNode(audioCtx, 'pcm-processor');
  workletNode.port.onmessage = (ev) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(ev.data); // ArrayBuffer Int16 PCM
    }
  };
  // Khong noi workletNode -> destination de tranh vong lap am thanh.
  sourceNode.connect(workletNode);

  startBtn.disabled = true;
  stopBtn.disabled = false;
  setStatus('Dang nghe & dich...', true);
}

function stop() {
  if (workletNode) { workletNode.disconnect(); workletNode = null; }
  if (sourceNode) { sourceNode.disconnect(); sourceNode = null; }
  if (audioCtx) { audioCtx.close(); audioCtx = null; }
  if (mediaStream) { mediaStream.getTracks().forEach((t) => t.stop()); mediaStream = null; }
  if (ws) { ws.close(); ws = null; }
  startBtn.disabled = false;
  stopBtn.disabled = true;
  setStatus('Da dung');
}

startBtn.addEventListener('click', start);
stopBtn.addEventListener('click', stop);
