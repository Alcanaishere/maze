
const CFG = {
  W:640, H:360,
  MAP_W:21, MAP_H:21,
  CELL:40,
  FOV: Math.PI/3,
  RAYS: 320,
  SPEED: 2.8,
  ROT_SPEED: 0.038,
  MOUSE_SENS: 0.0025,
  MM_CELL: 7,
};
const MAX_D = CFG.MAP_W * CFG.CELL;


const gc  = document.getElementById('gameCanvas');
const ctx = gc.getContext('2d');
gc.width  = CFG.W; gc.height = CFG.H;

const mm   = document.getElementById('minimapCanvas');
const mctx = mm.getContext('2d');
mm.width   = CFG.MAP_W * CFG.MM_CELL;
mm.height  = CFG.MAP_H * CFG.MM_CELL;
mm.style.height = mm.height + 'px';

const cp   = document.getElementById('compassCanvas');
const cctx = cp.getContext('2d');

const imgData = ctx.createImageData(CFG.W, CFG.H);
const pix     = imgData.data;

function setPx(x,y,r,g,b){
  const i=(y*CFG.W+x)*4; pix[i]=r; pix[i+1]=g; pix[i+2]=b; pix[i+3]=255;
}


function generateMaze(w,h){
  const m=Array.from({length:h},()=>new Uint8Array(w).fill(1));
  const carve=(cx,cy)=>{
    m[cy][cx]=0;
    [[0,-2],[0,2],[-2,0],[2,0]].sort(()=>Math.random()-0.5)
      .forEach(([dx,dy])=>{
        const nx=cx+dx,ny=cy+dy;
        if(nx>0&&nx<w-1&&ny>0&&ny<h-1&&m[ny][nx]){
          m[cy+dy/2][cx+dx/2]=0; carve(nx,ny);
        }
      });
  };
  carve(1,1); return m;
}

function floorCells(m){
  const r=[];
  for(let y=0;y<m.length;y++)
    for(let x=0;x<m[y].length;x++)
      if(!m[y][x]) r.push([x,y]);
  return r;
}


function castRay(m,wx,wy,ang){
  const rc=Math.cos(ang), rs=Math.sin(ang);
  let mx=(wx/CFG.CELL)|0, my=(wy/CFG.CELL)|0;
  const ddx=rc===0?1e30:Math.abs(CFG.CELL/rc);
  const ddy=rs===0?1e30:Math.abs(CFG.CELL/rs);
  let sx,sy,sdx,sdy;
  if(rc<0){sx=-1;sdx=(wx-mx*CFG.CELL)/Math.abs(rc);}
  else    {sx= 1;sdx=((mx+1)*CFG.CELL-wx)/Math.abs(rc);}
  if(rs<0){sy=-1;sdy=(wy-my*CFG.CELL)/Math.abs(rs);}
  else    {sy= 1;sdy=((my+1)*CFG.CELL-wy)/Math.abs(rs);}
  let side=0;
  for(let i=0;i<MAX_D;i++){
    if(sdx<sdy){sdx+=ddx;mx+=sx;side=0;}
    else       {sdy+=ddy;my+=sy;side=1;}
    if(my<0||my>=m.length||mx<0||mx>=m[0].length) break;
    if(m[my][mx]){
      const d=side===0
        ?(mx-wx/CFG.CELL+(1-sx)/2)/rc*CFG.CELL
        :(my-wy/CFG.CELL+(1-sy)/2)/rs*CFG.CELL;
      return [Math.abs(d),side];
    }
  }
  return [MAX_D,0];
}


function render3D(m,wx,wy,ang,gx,gy){
  const H=CFG.H, W=CFG.W, half=H>>1;

  for(let y=0;y<H;y++){
    const t=y<half ? y/half : (y-half)/(H-half);
    const r=y<half?Math.round(10+t*18):Math.round(28+t*12);
    const b=y<half?Math.round(28+t*48):Math.round(28);
    for(let x=0;x<W;x++) setPx(x,y,r,r,b);
  }
  const sw=Math.ceil(W/CFG.RAYS);
  let ra=ang-CFG.FOV/2;
  const da=CFG.FOV/CFG.RAYS;
  for(let i=0;i<CFG.RAYS;i++,ra+=da){
    const [dist,side]=castRay(m,wx,wy,ra);
    const cor=Math.max(dist*Math.cos(ra-ang),0.1);
    const wh=Math.min((CFG.CELL*H/cor)|0,H);
    const top=(half-wh/2)|0;
    let br=Math.max(0,Math.min(255,255-cor*0.85))|0;
    if(side===1) br=(br*0.65)|0;
    const x0=i*sw;
    for(let s=0;s<sw&&x0+s<W;s++)
      for(let y=top;y<top+wh&&y<H;y++) setPx(x0+s,y,br,br,br);
  }

  const gwx=gx*CFG.CELL+CFG.CELL/2, gwy=gy*CFG.CELL+CFG.CELL/2;
  const ddx=gwx-wx, ddy=gwy-wy;
  const gd=Math.hypot(ddx,ddy);
  if(gd>0){
    let rel=Math.atan2(ddy,ddx)-ang;
    while(rel> Math.PI) rel-=2*Math.PI;
    while(rel<-Math.PI) rel+=2*Math.PI;
    if(Math.abs(rel)<CFG.FOV/2){
      const sx=((rel/CFG.FOV+0.5)*W)|0;
      const cor=Math.max(gd*Math.cos(rel),0.1);
      const gh=Math.min((CFG.CELL*H/cor)|0,H);
      const gt=(half-gh/2)|0;
      const br=Math.max(60,Math.min(255,255-cor*0.5))|0;
      for(let y=gt;y<gt+gh&&y<H;y++)
        for(let s=-3;s<=3;s++){const xx=sx+s;if(xx>=0&&xx<W)setPx(xx,y,0,br,(br*0.5)|0);}
    }
  }
  ctx.putImageData(imgData,0,0);
}


function drawMinimap(m,wx,wy,ang,gx,gy){
  const S=CFG.MM_CELL;
  mctx.fillStyle='#050a06'; mctx.fillRect(0,0,mm.width,mm.height);
  for(let y=0;y<m.length;y++)
    for(let x=0;x<m[y].length;x++)
      if(m[y][x]){mctx.fillStyle='#00ff88';mctx.fillRect(x*S,y*S,S,S);}
  mctx.fillStyle='#00ffcc'; mctx.fillRect(gx*S+1,gy*S+1,S-2,S-2);
  const ppx=wx/CFG.CELL*S, ppy=wy/CFG.CELL*S;
  mctx.fillStyle='#ffe040'; mctx.beginPath(); mctx.arc(ppx,ppy,S/2,0,Math.PI*2); mctx.fill();
  mctx.strokeStyle='#ffe040'; mctx.lineWidth=1.5; mctx.beginPath();
  mctx.moveTo(ppx,ppy); mctx.lineTo(ppx+Math.cos(ang)*S*2.5, ppy+Math.sin(ang)*S*2.5); mctx.stroke();
}


function drawCompass(ang){
  const cx=50,cy=50,r=38;
  cctx.clearRect(0,0,100,100);
  cctx.fillStyle='rgba(0,255,136,0.07)'; cctx.beginPath(); cctx.arc(cx,cy,r,0,Math.PI*2); cctx.fill();
  cctx.strokeStyle='rgba(0,255,136,0.3)'; cctx.lineWidth=1; cctx.stroke();
  for(let i=0;i<8;i++){
    const a=i*Math.PI/4, inner=i%2===0?r-10:r-6;
    cctx.strokeStyle=i%2===0?'#00ff88':'#00aa55'; cctx.lineWidth=i%2===0?1.5:1;
    cctx.beginPath(); cctx.moveTo(cx+Math.cos(a)*inner,cy+Math.sin(a)*inner);
    cctx.lineTo(cx+Math.cos(a)*(r-2),cy+Math.sin(a)*(r-2)); cctx.stroke();
  }
  const na=-Math.PI/2-ang;
  cctx.fillStyle='#ff4455'; cctx.font='bold 11px monospace';
  cctx.textAlign='center'; cctx.textBaseline='middle';
  cctx.fillText('N', cx+Math.cos(na)*(r-14), cy+Math.sin(na)*(r-14));
  cctx.save(); cctx.translate(cx,cy); cctx.rotate(-ang);
  cctx.fillStyle='#ff4455'; cctx.beginPath(); cctx.moveTo(0,-r+8); cctx.lineTo(4,0); cctx.lineTo(-4,0); cctx.closePath(); cctx.fill();
  cctx.fillStyle='#00ff88'; cctx.beginPath(); cctx.moveTo(0,r-8); cctx.lineTo(4,0); cctx.lineTo(-4,0); cctx.closePath(); cctx.fill();
  cctx.restore();
}


function updateHUD(wx,wy,ang,gx,gy,total){
  const d=Math.hypot(wx-gx*CFG.CELL-CFG.CELL/2, wy-gy*CFG.CELL-CFG.CELL/2);
  document.getElementById('distFill').style.width=(Math.max(0,1-d/total)*100)+'%';
  const deg=(((ang*180/Math.PI)%360)+360)%360;
  const dirs=['E','NE','N','NW','W','SW','S','SE'];
  document.getElementById('dirVal').textContent=dirs[Math.round(deg/45)%8];
  document.getElementById('posVal').textContent=`${(wx/CFG.CELL).toFixed(1)},${(wy/CFG.CELL).toFixed(1)}`;
}


function isWall(m,x,y,mg=8){
  return [[-1,-1],[1,-1],[-1,1],[1,1]].some(([dx,dy])=>{
    const mx=((x+dx*mg)/CFG.CELL)|0, my=((y+dy*mg)/CFG.CELL)|0;
    return my>=0&&my<m.length&&mx>=0&&mx<m[0].length&&m[my][mx];
  });
}


const keys={};
let mdx=0, G=null;

function newGame(){
  const maze=generateMaze(CFG.MAP_W,CFG.MAP_H);
  const fl=floorCells(maze);
  const [sx,sy]=fl[0];
  const spx=sx*CFG.CELL+CFG.CELL/2, spy=sy*CFG.CELL+CFG.CELL/2;
  const [gx,gy]=fl.reduce((b,c)=>
    Math.abs(c[0]-sx)+Math.abs(c[1]-sy)>Math.abs(b[0]-sx)+Math.abs(b[1]-sy)?c:b);
  const total=Math.hypot(spx-gx*CFG.CELL-CFG.CELL/2, spy-gy*CFG.CELL-CFG.CELL/2);
  G={maze,px:spx,py:spy,angle:0,gx,gy,total,won:false};
}


function loop(){
  requestAnimationFrame(loop);
  if(!G) return;
  if(!G.won){
    G.angle+=mdx*CFG.MOUSE_SENS; mdx=0;
    let mx=0,my=0;
    const strafe=G.angle+Math.PI/2;
    if(keys['ArrowUp']  ||keys['w']){mx+=Math.cos(G.angle)*CFG.SPEED;my+=Math.sin(G.angle)*CFG.SPEED;}
    if(keys['ArrowDown']||keys['s']){mx-=Math.cos(G.angle)*CFG.SPEED;my-=Math.sin(G.angle)*CFG.SPEED;}
    if(keys['ArrowLeft'] ||keys['a']){mx-=Math.cos(strafe)*CFG.SPEED;my-=Math.sin(strafe)*CFG.SPEED;}
    if(keys['ArrowRight']||keys['d']){mx+=Math.cos(strafe)*CFG.SPEED;my+=Math.sin(strafe)*CFG.SPEED;}
    if(!isWall(G.maze,G.px+mx,G.py)) G.px+=mx;
    if(!isWall(G.maze,G.px,G.py+my)) G.py+=my;
    const d=Math.hypot(G.px-G.gx*CFG.CELL-CFG.CELL/2,G.py-G.gy*CFG.CELL-CFG.CELL/2);
    if(d<CFG.CELL*0.65){G.won=true;showOverlay('CLEAR!','yay! you have made it!!','Next Maze(Press R)');}
  }
  render3D(G.maze,G.px,G.py,G.angle,G.gx,G.gy);
  drawMinimap(G.maze,G.px,G.py,G.angle,G.gx,G.gy);
  drawCompass(G.angle);
  updateHUD(G.px,G.py,G.angle,G.gx,G.gy,G.total);
}


function showOverlay(t,m,b){
  document.getElementById('overlayTitle').textContent=t;
  document.getElementById('overlayMsg').textContent=m;
  document.getElementById('overlayBtn').textContent=b;
  document.getElementById('overlay').classList.remove('hidden');
}
function hideOverlay(){ document.getElementById('overlay').classList.add('hidden'); }

document.getElementById('overlayBtn').addEventListener('click',()=>{
  newGame(); hideOverlay(); gc.requestPointerLock();
});


document.addEventListener('keydown',e=>{
  keys[e.key]=true;
  if(e.key==='r'||e.key==='R'){newGame();hideOverlay();}
  e.preventDefault();
});
document.addEventListener('keyup',e=>{keys[e.key]=false;});
document.addEventListener('mousemove',e=>{
  if(document.pointerLockElement===gc) mdx+=e.movementX;
});
gc.addEventListener('click',()=>gc.requestPointerLock());


newGame();
loop();
