'use strict';

(() => {
  const $ = (id) => document.getElementById(id);
  const canvas = $('panorama');
  const state = { yaw: 0, pitch: 0, fov: 65, rotate: false, ready: false, lost: false, width: 0, height: 0, activeId: null };
  const rad = Math.PI / 180;
  const clamp = (v, min, max) => Math.max(min, Math.min(max, v));
  let gl, program, texture, uniforms, currentImage, frame = 0, lastTime = 0, loadId = 0, toastTimer, dragDepth = 0;
  const pointers = new Map();
  let gesture = null;

  const vertex = `attribute vec2 aPosition;
    varying vec2 vPosition;
    void main() { vPosition=aPosition; gl_Position=vec4(aPosition,0.0,1.0); }`;
  const fragment = `precision highp float;
    varying vec2 vPosition;
    uniform sampler2D uImage;
    uniform float uAspect;
    uniform float uTanFov;
    uniform float uYaw;
    uniform float uPitch;
    const float PI=3.141592653589793;
    void main() {
      vec3 ray=normalize(vec3(vPosition.x*uAspect*uTanFov,vPosition.y*uTanFov,1.0));
      float cp=cos(uPitch), sp=sin(uPitch);
      ray=vec3(ray.x,ray.y*cp+ray.z*sp,ray.z*cp-ray.y*sp);
      float cy=cos(uYaw), sy=sin(uYaw);
      ray=vec3(ray.x*cy+ray.z*sy,ray.y,ray.z*cy-ray.x*sy);
      vec2 uv=vec2(fract(0.5+atan(ray.x,ray.z)/(2.0*PI)),0.5-asin(clamp(ray.y,-1.0,1.0))/PI);
      gl_FragColor=vec4(texture2D(uImage,uv).rgb,1.0);
    }`;

  function setupGL() {
    gl = canvas.getContext('webgl', { alpha: false, antialias: false, depth: false, preserveDrawingBuffer: false });
    if (!gl) throw new Error('This browser cannot display 360 photos with WebGL. Open this local viewer in a browser with graphics acceleration enabled.');
    function shader(type, source) {
      const s = gl.createShader(type);
      gl.shaderSource(s, source); gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) { const log=gl.getShaderInfoLog(s); gl.deleteShader(s); throw new Error(`The panorama renderer could not start: ${log}`); }
      return s;
    }
    const vs=shader(gl.VERTEX_SHADER,vertex), fs=shader(gl.FRAGMENT_SHADER,fragment);
    program=gl.createProgram(); gl.attachShader(program,vs); gl.attachShader(program,fs); gl.linkProgram(program);
    gl.deleteShader(vs); gl.deleteShader(fs);
    if (!gl.getProgramParameter(program,gl.LINK_STATUS)) throw new Error('The panorama renderer could not initialize.');
    gl.useProgram(program);
    const buffer=gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER,buffer);
    gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,-1,1,1,-1,1,1]),gl.STATIC_DRAW);
    const position=gl.getAttribLocation(program,'aPosition'); gl.enableVertexAttribArray(position); gl.vertexAttribPointer(position,2,gl.FLOAT,false,0,0);
    uniforms=Object.fromEntries(['uImage','uAspect','uTanFov','uYaw','uPitch'].map(name=>[name,gl.getUniformLocation(program,name)]));
    gl.uniform1i(uniforms.uImage,0);
    texture=null;
  }

  function uploadImage(image) {
    const max=Math.min(gl.getParameter(gl.MAX_TEXTURE_SIZE),8192);
    let source=image;
    const width=image.naturalWidth, height=image.naturalHeight;
    if (width>max || height>max) {
      const scale=Math.min(max/width,max/height);
      source=document.createElement('canvas'); source.width=Math.floor(width*scale); source.height=Math.floor(height*scale);
      const ctx=source.getContext('2d'); ctx.imageSmoothingQuality='high'; ctx.drawImage(image,0,0,source.width,source.height);
    }
    const next=gl.createTexture(); gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D,next);
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL,false);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR); gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);
    gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,source);
    if (gl.getError()!==gl.NO_ERROR) { gl.deleteTexture(next); gl.bindTexture(gl.TEXTURE_2D,texture); throw new Error('The image is too large for this browser’s graphics memory. Try a smaller stitched export.'); }
    if (texture) gl.deleteTexture(texture);
    texture=next;
    return source===image?null:[source.width,source.height];
  }

  function invalidate() { if (!frame && !document.hidden && state.ready && !state.lost) frame=requestAnimationFrame(render); }
  function render(time) {
    frame=0;
    if (!state.ready || state.lost || document.hidden) return;
    const delta=lastTime?Math.min((time-lastTime)/1000,.1):0; lastTime=time;
    if(state.rotate) state.yaw+=delta*6;
    state.yaw=((state.yaw+180)%360+360)%360-180;
    const ratio=Math.min(window.devicePixelRatio||1,2), w=Math.max(1,Math.round(canvas.clientWidth*ratio)), h=Math.max(1,Math.round(canvas.clientHeight*ratio));
    if(canvas.width!==w || canvas.height!==h) { canvas.width=w; canvas.height=h; }
    gl.viewport(0,0,w,h); gl.useProgram(program); gl.bindTexture(gl.TEXTURE_2D,texture);
    gl.uniform1f(uniforms.uAspect,w/h); gl.uniform1f(uniforms.uTanFov,Math.tan(state.fov*rad/2));
    gl.uniform1f(uniforms.uYaw,state.yaw*rad); gl.uniform1f(uniforms.uPitch,state.pitch*rad);
    gl.drawArrays(gl.TRIANGLES,0,6);
    $('heading-value').textContent=`${Math.round((state.yaw+360)%360)%360}°`;
    canvas.dataset.yaw=state.yaw.toFixed(2); canvas.dataset.pitch=state.pitch.toFixed(2); canvas.dataset.fov=state.fov.toFixed(1);
    if(state.rotate) invalidate();
  }
  function zoom(value) {
    state.fov=clamp(value,35,110); $('zoom').value=String(Math.round(state.fov));
    $('zoom').setAttribute('aria-valuetext',`${Math.round(state.fov)} degree field of view`);
    $('zoom-in').disabled=state.fov<=35; $('zoom-out').disabled=state.fov>=110; invalidate();
  }
  function setRotate(value) {
    state.rotate=value && state.ready && !state.lost;
    $('rotate').setAttribute('aria-pressed',String(state.rotate)); $('rotate').setAttribute('aria-label',state.rotate?'Pause auto-rotate':'Start auto-rotate');
    lastTime=0; invalidate();
  }
  function reset() { state.yaw=0;state.pitch=0;setRotate(false);zoom(65); used(); }
  function used() { $('gesture-hint').classList.add('used'); }
  function toast(message) {
    clearTimeout(toastTimer); $('toast').textContent=message; $('toast').hidden=false;
    toastTimer=setTimeout(()=>$('toast').hidden=true,7500);
  }
  function togglePanel(id, toggle, open) {
    $(id).hidden=!open; $(toggle).setAttribute('aria-expanded',String(open));
  }
  function closePanels() { togglePanel('samples-panel','samples-toggle',false);togglePanel('help-panel','help-toggle',false); }
  function updateActiveSamples() { document.querySelectorAll('.sample').forEach(b=>{ const active=b.dataset.id===state.activeId;b.classList.toggle('active',active); b.setAttribute('aria-pressed',String(active)); }); }

  async function loadPhoto(url, title, id=null, filename=title) {
    if(!gl || state.lost) { toast('The panorama renderer is unavailable. Reload the viewer after graphics access is restored.'); return; }
    const ticket=++loadId;
    $('loading').hidden=false; $('empty-state').hidden=true; setRotate(false); closePanels();
    const image=new Image(); image.decoding='async';
    try {
      image.src=url; await image.decode();
      if(ticket!==loadId) return;
      const {naturalWidth:width,naturalHeight:height}=image;
      if(!width || !height) throw new Error('This image could not be decoded. Choose a JPEG, PNG or WebP panorama.');
      if(Math.abs(width/height-2)>.02) throw new Error(`This image is ${width} × ${height}. Choose a stitched 2:1 panorama for a correct 360° view.`);
      const scaled=uploadImage(image);
      currentImage=image; state.width=width;state.height=height;state.activeId=id;state.ready=true;
      $('viewer').classList.remove('context-lost');
      $('photo-title').textContent=title; $('photo-title').title=filename;
      $('photo-meta').textContent=`${width.toLocaleString()} × ${height.toLocaleString()} · Equirectangular${scaled?' · Display scaled':''}`;
      $('bottom-ui').hidden=false; $('view-label').hidden=false; $('gesture-hint').classList.remove('used');
      $('announcer').textContent=`${title} opened. ${width} by ${height} pixels. Drag to explore.`;
      updateActiveSamples(); reset(); $('gesture-hint').classList.remove('used');
      if(scaled) toast(`Displayed at ${scaled[0]} × ${scaled[1]} to fit your graphics hardware. Your original file is unchanged.`);
    } catch(error) {
      if(ticket!==loadId) return;
      toast(error.message||'The photo could not be opened.');
      if(!state.ready) $('empty-state').hidden=false;
    } finally { if(ticket===loadId) $('loading').hidden=true; }
  }
  async function loadFile(file) {
    if(!file) return;
    if(/\.(insp|dng|insv)$/i.test(file.name)) { toast('This is an Insta360 original. Stitch it to a 2:1 JPEG panorama before opening it here.'); return; }
    if(!/\.(jpe?g|png|webp)$/i.test(file.name)) { toast('Choose a JPEG, PNG or WebP panorama.'); return; }
    const url=URL.createObjectURL(file);
    try { await loadPhoto(url,file.name,null,file.name); } finally { URL.revokeObjectURL(url); }
  }

  function gestureSnapshot() {
    const points=[...pointers.values()];
    if(!points.length) {gesture=null;return;}
    gesture={x:points.reduce((s,p)=>s+p.x,0)/points.length,y:points.reduce((s,p)=>s+p.y,0)/points.length,distance:points.length>1?Math.hypot(points[0].x-points[1].x,points[0].y-points[1].y):0};
  }
  canvas.addEventListener('pointerdown',e=>{
    if(!state.ready || e.button>0) return;
    closePanels();canvas.focus({preventScroll:true});setRotate(false);used();
    pointers.set(e.pointerId,{x:e.clientX,y:e.clientY});canvas.setPointerCapture(e.pointerId);canvas.classList.add('dragging');gestureSnapshot();
  });
  canvas.addEventListener('pointermove',e=>{
    if(!pointers.has(e.pointerId)) return;
    const before=gesture;pointers.set(e.pointerId,{x:e.clientX,y:e.clientY});gestureSnapshot();
    if(!before || !gesture) return;
    const sensitivity=state.fov/Math.max(canvas.clientHeight,1);
    state.yaw-=(gesture.x-before.x)*sensitivity;state.pitch=clamp(state.pitch+(gesture.y-before.y)*sensitivity,-89,89);
    if(gesture.distance && before.distance) zoom(state.fov*before.distance/gesture.distance);
    invalidate();
  });
  function pointerEnd(e) { pointers.delete(e.pointerId);gestureSnapshot();if(!pointers.size) canvas.classList.remove('dragging'); }
  for(const event of ['pointerup','pointercancel','lostpointercapture']) canvas.addEventListener(event,pointerEnd);
  canvas.addEventListener('wheel',e=>{ if(!state.ready) return;e.preventDefault();const d=e.deltaY*(e.deltaMode===1?16:e.deltaMode===2?canvas.clientHeight:1);zoom(state.fov+d*.04);used(); },{passive:false});
  canvas.addEventListener('dblclick',()=>reset());
  $('zoom').addEventListener('input',e=>{zoom(Number(e.target.value));used();});
  $('zoom-in').addEventListener('click',()=>{zoom(state.fov-8);used();});
  $('zoom-out').addEventListener('click',()=>{zoom(state.fov+8);used();});
  $('reset').addEventListener('click',reset);$('rotate').addEventListener('click',()=>{setRotate(!state.rotate);used();});
  async function fullscreen() {
    try { if(document.fullscreenElement) await document.exitFullscreen();else await $('viewer').requestFullscreen(); }
    catch { toast('Fullscreen is unavailable in this browser window. Open the local viewer in a regular browser tab to use it.'); }
  }
  $('fullscreen').addEventListener('click',fullscreen);
  document.addEventListener('fullscreenchange',()=>{ $('fullscreen').setAttribute('aria-label',document.fullscreenElement?'Exit fullscreen':'Enter fullscreen');invalidate(); });
  function chooseFile() { $('file-input').click(); }
  $('open-photo').addEventListener('click',chooseFile);$('empty-open').addEventListener('click',chooseFile);
  $('file-input').addEventListener('change',e=>{const file=e.target.files[0]; e.target.value='';void loadFile(file);});
  $('samples-toggle').addEventListener('click',()=>{ const open=$('samples-panel').hidden;closePanels();togglePanel('samples-panel','samples-toggle',open); });
  $('help-toggle').addEventListener('click',()=>{ const open=$('help-panel').hidden;closePanels();togglePanel('help-panel','help-toggle',open); });
  $('samples-close').addEventListener('click',()=>{togglePanel('samples-panel','samples-toggle',false);$('samples-toggle').focus();});
  $('help-close').addEventListener('click',()=>{togglePanel('help-panel','help-toggle',false);$('help-toggle').focus();});
  document.addEventListener('keydown',e=>{
    if(e.key==='Escape') {closePanels();$('toast').hidden=true;return;}
    if(e.ctrlKey || e.metaKey || e.altKey || e.isComposing || !state.ready || /^(INPUT|BUTTON|TEXTAREA|SELECT)$/.test(e.target.tagName) || e.target.isContentEditable) return;
    const step=e.shiftKey?10:3;
    switch(e.key.toLowerCase()) {
      case 'arrowleft':state.yaw-=step;break;case 'arrowright':state.yaw+=step;break;
      case 'arrowup':state.pitch=clamp(state.pitch+step,-89,89);break;case 'arrowdown':state.pitch=clamp(state.pitch-step,-89,89);break;
      case '+':case '=':zoom(state.fov-5);break;case '-':case '_':zoom(state.fov+5);break;
      case 'r':reset();break;case 'f':if(!e.repeat) void fullscreen();break;case ' ':if(!e.repeat) setRotate(!state.rotate);break;
      default:return;
    }
    e.preventDefault();used();invalidate();
  });
  document.addEventListener('dragenter',e=>{if(![...e.dataTransfer.types].includes('Files'))return;e.preventDefault();dragDepth++;$('drop-zone').hidden=false;});
  document.addEventListener('dragover',e=>{if([...e.dataTransfer.types].includes('Files')){e.preventDefault();e.dataTransfer.dropEffect='copy';}});
  document.addEventListener('dragleave',e=>{e.preventDefault();dragDepth=Math.max(0,dragDepth-1);if(!dragDepth)$('drop-zone').hidden=true;});
  document.addEventListener('drop',e=>{e.preventDefault();dragDepth=0;$('drop-zone').hidden=true;void loadFile(e.dataTransfer.files[0]);});
  window.addEventListener('resize',invalidate);document.addEventListener('visibilitychange',()=>{lastTime=0;invalidate();});
  canvas.addEventListener('webglcontextlost',e=>{e.preventDefault();state.lost=true;setRotate(false);$('viewer').classList.add('context-lost');toast('Graphics were interrupted. Restoring your panorama…');});
  canvas.addEventListener('webglcontextrestored',()=>{
    state.ready=false;
    try { setupGL();state.lost=false;if(currentImage){uploadImage(currentImage);state.ready=true;}$('viewer').classList.remove('context-lost');invalidate(); }
    catch(error){$('empty-state').hidden=false;$('bottom-ui').hidden=true;$('view-label').hidden=true;toast(error.message);}
  });

  async function start() {
    try {setupGL();zoom(65);} catch(error) { $('loading').hidden=true;$('empty-state').hidden=false;toast(error.message);return; }
    const initialLoad=loadId;
    try {
      const response=await fetch('/api/photos');if(!response.ok)throw new Error('Preloaded photos are unavailable. You can still open a local panorama.');
      const {photos,defaultId}=await response.json();
      $('samples-toggle').hidden=!photos.length;
      for(const photo of photos) {
        const button=document.createElement('button');button.className='sample';button.dataset.id=photo.id;button.setAttribute('aria-pressed','false');
        const image=document.createElement('img');image.className='sample-thumb';image.src=photo.url;image.alt='';image.loading='lazy';
        const text=document.createElement('span'),title=document.createElement('strong'),meta=document.createElement('small');title.textContent=photo.title;meta.textContent=`${photo.width.toLocaleString()} × ${photo.height.toLocaleString()}`;text.append(title,meta);button.append(image,text);
        button.addEventListener('click',()=>void loadPhoto(photo.url,photo.title,photo.id,photo.filename));$('sample-list').append(button);
      }
      if(!photos.length) {$('sample-list').textContent='Open a local panorama to get started.';if(loadId===initialLoad){$('loading').hidden=true;$('empty-state').hidden=false;}return;}
      if(loadId!==initialLoad) return;
      const selected=photos.find(p=>p.id===defaultId)||photos[0];await loadPhoto(selected.url,selected.title,selected.id,selected.filename);
    } catch(error) {if(loadId===initialLoad){$('loading').hidden=true;$('empty-state').hidden=state.ready;toast(error.message);}}
  }
  void start();
})();
