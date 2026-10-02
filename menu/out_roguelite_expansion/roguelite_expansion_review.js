'use strict';
const D=window.ART, $=s=>document.querySelector(s), C=$('#scene'), g=C.getContext('2d');
const images={}, tinted=new Map(), gold='#f0b429', bone='#f2efe4', muted='#a8b7ce';
let tab='combat', time=900, playing=true, last=0, W=854, H=480, node='root', toast='', toastUntil=0;
const select=id=>$(id).value, checked=id=>$(id).checked;
const tree={root:{title:'COMMAND',parent:null,items:[['MAGIC','magic'],['ITEM','item'],['SPECIAL','special']]},
 magic:{title:'MAGIC',parent:'root',items:[['CINDER','cinder'],['RIME','rime'],['REACTION','reaction']]},
 cinder:{title:'CINDER',parent:'magic',items:[['RELEASE',null],['STEP',null],['GUARD',null]]},
 rime:{title:'RIME',parent:'magic',items:[['SHATTER',null],['SKATE',null],['GUARD',null]]},
 reaction:{title:'REACTION',parent:'magic',items:[['THERMAL',null],['LOCKED',null],['LOCKED',null]]},
 item:{title:'ITEM',parent:'root',items:[['RESTORE',null],['CLEANSE',null],['EMPTY',null]]},
 special:{title:'SPECIAL',parent:'root',items:[['RELEASE',null],['GENE SHIFT',null],['BUILD',null]]}};
function choose(dir){
 if(dir==='up'){if(tree[node].parent)node=tree[node].parent;else notify('TAUNT · ROOT ONLY');}
 else{let item=tree[node].items[{left:0,right:1,down:2}[dir]];if(!item)return;
  if(item[1])node=item[1];else if(['LOCKED','EMPTY'].includes(item[0]))notify('UNAVAILABLE · CHOOSE ANOTHER BRANCH');
  else{notify(item[0]+' · ART PREVIEW');node='root';}}
 $('#command-help').textContent=node==='root'?'↑ Taunt at root. ↑ Back inside a branch.':'↑ Back to '+tree[tree[node].parent].title+' · no taunt';draw();
}
function notify(s){toast=s;toastUntil=performance.now()+2200;}
function path(points,fill,stroke,width=1){g.beginPath();points.forEach((p,i)=>i?g.lineTo(...p):g.moveTo(...p));g.closePath();if(fill){g.fillStyle=fill;g.fill();}if(stroke){g.strokeStyle=stroke;g.lineWidth=width;g.stroke();}}
function rect(x,y,w,h,color){g.fillStyle=color;g.fillRect(x,y,w,h);}
function txt(s,x,y,size=12,color=bone,align='left'){g.font=`${size}px Kit, sans-serif`;g.fillStyle=color;g.textAlign=align;g.fillText(s,x,y);}
function stroke(points,color,width=2,alpha=1){g.save();g.globalAlpha*=alpha;g.strokeStyle=color;g.lineWidth=width;g.lineCap='round';g.lineJoin='round';g.beginPath();points.forEach((p,i)=>i?g.lineTo(...p):g.moveTo(...p));g.stroke();g.restore();}
function image(name,x,y,w,h=w,color=bone,alpha=1,angle=0){
 const src=images[name];if(!src)return;
 const key=name+color;let canvas=tinted.get(key);
 if(!canvas){canvas=document.createElement('canvas');canvas.width=src.width;canvas.height=src.height;let c=canvas.getContext('2d');c.drawImage(src,0,0);c.globalCompositeOperation='source-in';c.fillStyle=color;c.fillRect(0,0,canvas.width,canvas.height);tinted.set(key,canvas);}
 g.save();g.globalAlpha*=alpha;g.translate(x,y);g.rotate(angle);g.drawImage(canvas,-w/2,-h/2,w,h);g.restore();
}
function plate(x,y,w,h,accent=gold){path([[x+7,y],[x+w,y],[x+w-7,y+h],[x,y+h]],'#101a2eee','#35445a');rect(x+5,y+5,2,h-10,accent);}
function smallLabel(text,x,y,color=gold){txt(text,x,y,9,color);}
function phase(){return select('#state');}
function motion(){return checked('#reduced')?0:time/1000;}
function family(){return D.families[select('#family')];}
function body(x,y,t,scale=1,color='#b9c8dd',ghost=false,facing=1,weapon=false){
 // Entirely original articulated drawing. y is the ground contact point.
 g.save();g.translate(x,y);g.scale(scale*facing,scale);
 let sway=ghost?0:Math.sin(t*4)*2, step=Math.sin(t*4)*5;
 if(ghost)g.globalAlpha*=.28;
 stroke([[-11,-30],[-19+step,-15],[-23+step,-2]],ghost?color:'#60758f',10);
 stroke([[4,-32],[13-step,-18],[18-step,-2]],color,11);
 path([[-19,-68],[5,-71],[15,-40],[-8,-28],[-20,-42]],ghost?color:'#263d5c',color,1.5);
 path([[-18,-65],[2,-69],[8,-56],[-14,-50]],color);
 stroke([[-14,-59],[-28,-46+sway],[-13,-38+sway]],color,9);
 stroke([[5,-61],[23,-53+sway],[33,-62+sway]],color,9);
 path([[-13,-78],[-10,-91],[4,-94],[14,-84],[7,-73],[-7,-73]],color);
 if(!ghost){path([[0,-86],[12,-83],[7,-80],[0,-80]],'#101b2b');rect(-26+step,-5,15,5,bone);rect(13-step,-5,17,5,bone);}
 if(weapon){stroke([[32,-62+sway],[59,-96+sway]],ghost?color:'#d5dfeb',5);stroke([[25,-65+sway],[38,-55+sway]],gold,3);}
 g.restore();
}
function background(theme='cobalt',empty=false){
 let top={cobalt:'#071329',fire:'#201211',frost:'#0b1b27'}[theme], accent={cobalt:'#657fc2',fire:'#a96c46',frost:'#548f9d'}[theme];
 let grad=g.createLinearGradient(0,0,0,H);grad.addColorStop(0,top);grad.addColorStop(1,'#070e18');g.fillStyle=grad;g.fillRect(0,0,W,H);
 if(empty){image('theme_'+(theme==='cobalt'?'ribs':theme==='fire'?'embers':'frost'),W*.72,H*.42,310,350,accent,.12);return;}
 for(let i=0;i<9;i++){let x=i*130-70;path([[x,0],[x+70,0],[x+120,305],[x+50,305]],'#0f1c30');stroke([[x+71,0],[x+121,303]],accent,1,.17);}
 let floor=H-106;
 rect(0,floor,W,17,'#314764');rect(0,floor,W,2,'#8ba2b9');rect(0,floor+17,W,H-floor-17,'#080e18');
 for(let x=0;x<W;x+=95){stroke([[x,floor+2],[x+9,floor+15]],'#697a8f',1,.5);rect(x+18,floor+11,22,2,accent);}
 // Door illustration preserves tall opening and modular lintel proportions.
 const dx=W-110,dy=floor-118;
 rect(dx-8,dy-8,85,127,'#263d59');rect(dx,dy,69,118,'#0a1423');stroke([[dx,dy+118],[dx,dy],[dx+69,dy],[dx+69,dy+118]],'#778eae',3);
 for(let yy=dy+5;yy<floor;yy+=12)stroke([[dx+6,yy],[dx+63,yy]],accent,1,.15);
 image('door_'+select('#door'),dx+35,dy-25,29,29,select('#door')==='locked'?'#e9b8a3':gold,.9);
}
function charges(x,y,count,capacity,color,scale=1){
 for(let i=0;i<capacity;i++)image('charge_segment',x+i*10*scale,y,12*scale,8*scale,i<count?color:'#40516c',1);
}
function halo(f,x,y,sz,t,state){
 let op=D.states[state].opacity, n=state==='dormant'?0:state==='charging'?2:state==='recovery'?0:3;
 image(f.halo,x,y,sz,sz,f.color,op*.65,f.name==='Rime'?0:t*.3);
 for(let i=0;i<3;i++)image('halo_sector',x,y,sz+8,sz+8,f.color,i<n?.8:.13,i*Math.PI*2/3);
}
function identity(x,y,t,f,state,placement='traversal',scale=1,other=false){
 const reduced=checked('#reduced'),q=D.quality[select('#quality')],cfg=D.states[state],moving=!reduced;
 const dx=moving?Math.sin(t*1.2)*27:0, weapon=placement==='assault';
 let anchor={traversal:[-2,-8],assault:[weapon?52:30,weapon?-84:-56],guard:[-4,-49]}[placement];
 const history=(state==='dormant'||reduced)?0:q.afterimages;
 if(checked('#ghosts')&&moving){for(let i=history;i>0;i--){g.save();g.globalAlpha*=.52/i;body(x+dx-i*17,y,t-i*.16,scale,f.color,true,1,weapon);g.restore();}}
 if(f.trail&&state!=='dormant'&&moving){
  let points=[];for(let i=q.trail_samples;i>=0;i--){let u=i/q.trail_samples;points.push([x+dx+anchor[0]*scale-u*110*scale,y+anchor[1]*scale+Math.sin(t*3-u*4)*7*scale]);}
  stroke(points,f.color,placement==='guard'?2:4,.34);
  for(let j=0;j<3;j++)image(f.trail,x+dx-26*scale-j*25*scale,y+anchor[1]*scale,90*scale,35*scale,f.color,(.45-j*.12)*cfg.opacity,0);
 }
 if(placement==='guard')halo(f,x+dx-2*scale,y-50*scale,85*scale,t,state);
 if(placement==='traversal'){g.save();g.translate(x+dx,y-2);g.scale(1,.3);halo(f,0,0,65*scale,t,state);g.restore();}
 body(x+dx,y,t,scale,other?'#8c9cb6':'#d0d9e6',false,1,weapon);
 // Material concept overlay constrained to original mannequin regions only.
 if(f.surface){g.save();g.beginPath();let ax=x+dx+anchor[0]*scale,ay=y+anchor[1]*scale;
   g.rect(ax-15*scale,ay-20*scale,30*scale,30*scale);g.clip();image(f.surface,ax,ay,46*scale,48*scale,f.color,cfg.opacity);g.restore();}
 if(placement==='assault')halo(f,x+dx+anchor[0]*scale,y+anchor[1]*scale,40*scale,t,state);
 let orb=reduced?0:Math.min(q.orbitals,cfg.orbit_count);
 for(let i=0;i<orb;i++){let a=t*.8+i*Math.PI*2/orb;image(f.orbit,x+dx+Math.cos(a)*47*scale,y-54*scale+Math.sin(a)*27*scale,17*scale,25*scale,f.color,.65,a*.3);}
 if(state==='activation')image(f.trail||'halo_sector',x+dx+20*scale,y-44*scale,110*scale,80*scale,f.color,.65,Math.sin(t)*.3);
 image(other?'map_unseen':'map_current',x+dx,y+13*scale,14*scale,14*scale,other?'#c6abc9':gold,.8);
}
function hud(){
 let f=family();plate(17,H-78,154,57,f.color);txt('37%',31,H-43,27);txt('× 3',104,H-46,12,muted);txt('P1',31,H-63,8,gold);
 image(f.icon,32,H-29,11,11,f.color);charges(43,H-29,phase()==='charging'?2:phase()==='ready'?3:0,3,f.color,.65);
 image('icon_traversal',81,H-29,11,11,muted);charges(91,H-29,1,3,'#abedaa',.65);
 image('icon_guard',129,H-29,11,11,muted);charges(140,H-29,2,3,'#91e5f4',.65);
 image('icon_item',144,H-50,10,10,bone);txt('2',152,H-46,9,bone);
 let open=node!=='root',w=open?210:232,h=open?76:30,x=W-w-17,y=H-h-22;
 plate(x,y,w,h);if(open){txt('↑ BACK',x+14,y+14,8,muted);txt('MAGIC / '+tree[node].title,x+w-16,y+14,8,gold,'right');}
 tree[node].items.forEach((it,i)=>{let xx=x+13+i*(w-23)/3,yy=y+(open?39:19);txt(['←','→','↓'][i],xx,yy,13,gold);txt(it[0],xx+16,yy,9,bone);if(open){rect(xx,y+48,(w-30)/3-6,2,'#40506b');}});
 if(open)txt('DIRECTION TO CHOOSE',x+14,y+66,7,muted);
 if(toast&&performance.now()<toastUntil){plate(W/2-110,22,220,28);txt(toast,W/2,40,9,bone,'center');}
 smallLabel({cobalt:'COBALT HALLS',fire:'EMBER COURT',frost:'RIME GALLERY'}[select('#theme')],20,24,muted);txt('03 / 14',W-20,24,9,muted,'right');
 // Mini map stays off the center of combat.
 for(let i=0;i<4;i++){if(i)stroke([[25+(i-1)*19,42],[25+i*19,42]],'#64748a',1);image(i===2?'map_current':i<2?'map_seen':'map_unseen',25+i*19,42,12,12,i===2?gold:muted);}
}
function combat(){background(select('#theme'));let t=motion();identity(W*.39,H-106,t,family(),phase(),'traversal',1.05);if(checked('#opponent'))identity(W*.64,H-106,t+.8,D.families.frost,'charging','assault',.97,true);hud();}
function bodyScene(){
 background('cobalt',true);let f=family(),t=motion(),s=phase(),place=select('#placement');
 txt(f.name.toUpperCase(),30,42,12,f.color);txt(D.families[select('#family')].shape,30,61,10,muted);
 let x=checked('#opponent')?W*.37:W*.51;
 identity(x,H*.72,t,f,s,place,2.2);
 if(checked('#opponent'))identity(W*.76,H*.72,t+.6,D.families.frost,s,place,1.55,true);
 stroke([[30,H-58],[W-30,H-58]],'#30405a',1);txt(s.toUpperCase(),30,H-35,14,bone);txt('01 / '+place.toUpperCase(),W-30,H-35,11,f.color,'right');
}
function founder(key,x,y,size,t,weight=1,phaseName='ready',shared=false){
 if(weight<=0)return;let f=D.founders[key],reduced=checked('#reduced'),q=D.quality[select('#quality')];
 let local=reduced?0:t,decay=phaseName==='recovery'?.26:phaseName==='charging'?.45:phaseName==='dormant'?.18:.8;
 let detailBudget=Math.min(shared?4:6,q.decorative_layers);
 g.save();g.globalAlpha*=weight*decay;
 if(key==='SolarEruption'){
  image(f.ring,x,y,size*.88,size*.88,f.color,.38,local*.15);
  for(let i=0;i<Math.min(5,detailBudget);i++){let a=i*Math.PI*2/5+local*.35;image(f.core,x+Math.cos(a)*size*.25,y+Math.sin(a)*size*.29,size*.36,size*.56,f.color,.85,a+.2);}
 }else if(key==='GlacialShatter'){
  image(f.ring,x,y,size*.96,size*.96,f.color,.72,0);
  for(let i=0;i<Math.min(6,detailBudget);i++){let a=i*Math.PI/3;image(f.core,x+Math.cos(a)*size*.32,y+Math.sin(a)*size*.32,size*.22,size*.43,f.color,.8,a+Math.PI/2);}
 }else if(key==='ThunderCrown'){
  for(let i=0;i<Math.min(5,detailBudget);i++){let a=-Math.PI*.92+i*Math.PI*.21;let alpha=reduced?.8:.55+.22*Math.sin(local*2-i*.8);image(f.core,x+Math.cos(a)*size*.33,y+Math.sin(a)*size*.33,size*.33,size*.5,f.color,alpha,a+Math.PI/2);}
  image(f.detail,x,y-size*.3,size*.86,size*.3,f.color,.75);
 }else if(key==='AstralVortex'){
  image(f.core,x,y,size,size*.8,f.color,.8,local*.5);image(f.core,x,y,size*.74,size*.61,'#829cff',.6,-local*.7+Math.PI);
  image(f.ring,x,y,size*.62,size*.62,'#e9d8ff',.5,-local*.2);
 }else{
  image(f.core,x,y,size*1.2,size,f.color,.9,-.4+Math.sin(local)*.2);
  image(f.core,x-12,y+14,size*.9,size*.74,f.color,.3,-.6);
  image(f.ring,x+size*.36,y-size*.12,size*.2,size*.2,bone,.85,local*.4);
 }
 g.restore();
}
function founderScene(){
 background('cobalt',true);let mode=select('#mode'),a=select('#parentA'),b=select('#parentB'),mix=+select('#mix')/100,t=motion(),p='ready';
 let title=D.founders[a].title,caption='AUTHORED FOUNDER · CHARGE / RELEASE / DECAY';
 // Deterministic 4-second review cycle: hold / charge / activation / recovery.
 p=checked('#reduced')?'ready':time<700?'dormant':time<1700?'charging':time<2700?'activation':'recovery';
 if(mode==='reaction'){let r=D.reactions[select('#reaction')];a=r.parents[0];b=r.parents[1];mix=.5;title=r.title;caption=r.sequence.toUpperCase();}
 if(mode==='blend')title=D.founders[a].title+' × '+D.founders[b].title;
 let s=H*.51,x=W*.5,y=H*.48;
 if(mode==='single')founder(a,x,y,s,t,1,p);
 else if(mode==='blend'){
  // Exact endpoints. Each authored midpoint has its own composition.
  if(mix===0||a===b)founder(a,x,y,s,t,1,p);
  else if(mix===1)founder(b,x,y,s,t,1,p);
  else{
   let plan=D.blends.find(v=>v.parents.includes(a)&&v.parents.includes(b));let reversed=plan.parents[0]!==a;
   let transforms=[plan.composition.parent_a_transform,plan.composition.parent_b_transform];if(reversed)transforms.reverse();
   let bend=Math.sin(mix*Math.PI);
   [a,b].forEach((key,i)=>{let tr=transforms[i];g.save();g.translate(x+tr[0]*bend,y+tr[1]*bend);g.rotate(tr[2]*bend);founder(key,0,0,s*(1+(tr[3]-1)*bend),t,Math.sqrt(i?mix:1-mix),p,true);g.restore();});
  }
 }else{
  let u=checked('#reduced')?.5:(time%4000)/4000,id=select('#reaction');
  let configs={thermal_shock:[0,0,0,0,1,.9],plasma_surge:[u*35,8,-12,-20,.85,1],charged_crystals:[0,14,0,-20,1,.8],fire_cyclone:[-15,8,12,-3,.8,1.1],orbital_shard_storm:[Math.cos(t)*18,Math.sin(t)*18,0,0,1.15,.8],infused_comet:[-35*(1-u),15,24*u,-6,.7,1.1]};
  let c=configs[id];founder(a,x+c[0],y+c[1],s*c[4],t,u<.35?.55:.85,p,true);founder(b,x+c[2],y+c[3],s*c[5],-t,u<.35?.85:.55,p,true);
 }
 body(x,y+55,t,1.12,'#a9b8ce');
 txt(title,30,37,20,bone);txt(mode==='blend'?`${Math.round((1-mix)*100)} / ${Math.round(mix*100)} · SHARED LAYER BUDGET`:caption,30,58,9,muted);
 const labels=['DORMANT','CHARGING','ACTIVATION','RECOVERY'];
 labels.forEach((label,i)=>{let xx=32+i*(W-64)/4;rect(xx,H-57,(W-76)/4,3,label.toLowerCase()===p?gold:'#33445e');txt(label,xx,H-37,9,label.toLowerCase()===p?gold:muted);});
}
function card(x,y,w,title,icon,accent,detail,selected=false){
 plate(x,y,w,130,accent);if(selected)stroke([[x+7,y],[x+w,y]],accent,3);
 image(icon,x+23,y+25,23,23,accent);txt(title,x+16,y+62,14,bone);txt(detail,x+16,y+83,9,muted);stroke([[x+16,y+94],[x+w-16,y+94]],'#33465e',1);txt('PREVIEW BEFORE COMMIT',x+16,y+113,8,accent);
}
function world(){
 background(select('#theme'));let p=select('#presentation'),t=motion();
 if(p==='tells'){
  let tells=['dash','guard','zone','dive','phase'];tells.forEach((id,i)=>{let x=60+i*(W-120)/4;body(x,H-106,t+i*.3,.8);image('tell_'+id,x,H-245,38,38,i===4?gold:'#f0b098',.9);txt(id.toUpperCase(),x,H-279,9,muted,'center');});
  txt('TELEGRAPH THE OPENING.',30,45,24);txt('Shapes and directions are tied to real intent. Timings come from the action system.',30,67,10,muted);
 }else if(p==='reward'){
  rect(0,0,W,H,'#08101bd9');txt('CHOOSE YOUR NEXT EDGE.',32,65,27);txt('One committed change. A clear benefit, a clear cost.',32,88,11,muted);
  let w=(W-88)/3;card(30,133,w,'HEAVY EMBER','icon_cinder','#ff985b','POWER ↑ / RECHARGE SLOWER',true);card(44+w,133,w,'WARDING CHARM','equip_charm','#91e5f4','CAPACITY ↑ / EQUIPMENT SLOT');card(58+w*2,133,w,'QUICK CADENCE','family_kinetic','#abedaa','RECHARGE FASTER / POWER ↓');
  txt('← CHOOSE',44,294,10,gold);txt('→ CHOOSE',58+w,294,10,muted);txt('↓ CHOOSE',72+w*2,294,10,muted);txt('Values supplied by the committed build. Example choices shown.',32,H-37,10,muted);
 }else if(p==='fusion'){
  rect(0,0,W,H,'#08101bcc');txt('TWO HISTORIES. ONE BUILD.',32,55,27);let u=checked('#reduced')?1:Math.min(1,time/1800),a=W*.5-130*(1-u),b=W*.5+130*(1-u);
  image('halo_cinder',a,H*.47,140,140,'#ff985b',.5,t*.3);image('halo_rime',b,H*.47,112,112,'#91e5f4',.6,-t*.25);
  image('icon_cinder',a-25,H*.47,42,42,'#ff985b',1-u*.4);image('icon_rime',b+25,H*.47,42,42,'#91e5f4',1-u*.4);
  txt(u<1?'PREVIEWING INHERITANCE':'THERMAL ANCESTRY',W*.5,H*.73,18,bone,'center');txt('Visual preview · gameplay commit and costs supplied by runtime',W*.5,H*.8,10,muted,'center');
 }else if(p==='transition'){
  identity(W*.4,H-106,t,D.families.fire,'dormant');let u=time/4000,cover=u<.25?u*4:u<.65?1:(1-u)/.35;
  for(let i=0;i<8;i++){let x=i*W/8;g.save();g.beginPath();g.rect(x,0,W/8+1,H);g.clip();path([[x-60,-H+H*2*cover],[x+W/8+60,-H+H*2*cover],[x+W/8,H*2*cover],[x-120,H*2*cover]],'#101b2d');g.restore();}
  if(cover>.95){image('icon_route',W/2,H/2-25,40,40,gold);txt('RIME GALLERY',W/2,H/2+22,20,bone,'center');txt('REVEAL WHEN THE ROOM IS READY',W/2,H/2+44,9,muted,'center');}
 }else{
  rect(0,0,W,H,'#07101bea');let win=p==='victory';image(win?'reward_extract':'icon_gene',W/2,105,52,52,win?gold:muted);
  txt(win?'RUN COMPLETE.':'THE RUN ENDS HERE.',W/2,176,30,bone,'center');txt(win?'Choose the gene you carry forward.':'Your collection is retained.',W/2,201,12,muted,'center');
  plate(W/2-150,237,300,80,win?gold:'#7b8da7');image('icon_cinder',W/2-118,276,32,32,'#ff985b');txt(win?'CINDER DRIVE':'CINDER / RIME',W/2-87,268,16);txt(win?'PREVIEW EXPORT → CONFIRM':'Run-only upgrades expire.',W/2-87,290,10,muted);
  txt(win?'Export only after save succeeds.':'Review build     /     Return to collection',W/2,358,11,win?gold:muted,'center');
 }
}
function draw(){
 W=(select('#aspect')==='four'||tab==='identity'||tab==='founders')?640:854;H=480;
 if(C.width!==W*2){C.width=W*2;C.height=H*2;C.style.aspectRatio=W+'/'+H;}
 g.setTransform(2,0,0,2,0,0);g.clearRect(0,0,W,H);
 if(tab==='combat')combat();else if(tab==='identity')bodyScene();else if(tab==='founders')founderScene();else if(tab==='world')world();
 $('#time-label').textContent=(time/1000).toFixed(2)+' / 04.00';$('#scrub').value=Math.floor(time);
}
function setTab(value){tab=value;document.querySelectorAll('[data-tab]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.tab===tab));$('#review').hidden=tab==='library';$('#library').hidden=tab!=='library';
 document.querySelectorAll('[data-for]').forEach(e=>e.hidden=!e.dataset.for.split(' ').includes(tab));
 const text={combat:['01 / IN THE FIGHT','Keep the stage clear.','Small status at the edges. Directional choices appear only while navigating the tree.'],identity:['02 / CONTINUOUS IDENTITY','Wear the build.','Boots carry motion. Hands carry intent. The torso carries protection.'],founders:['03 / FOUNDER LANGUAGE','Shape before spectacle.','Five authored compositions, ten parent blends, six timed reactions.'],world:['04 / BETWEEN FIGHTS','Give changes weight.','Room identity, readable threats, and a clear outcome for every run.']};
 if(text[tab]){let [a,b,c]=text[tab];$('#panel-number').textContent=a;$('#panel-title').textContent=b;$('#panel-copy').textContent=c;$('#scene-label').textContent=a+' / ART PREVIEW';}
 $('#blend-strip').hidden=tab!=='founders';
 $('#annotation').textContent=tab==='identity'?'Original mannequin art direction. Afterimages need native pose history; ribbons need attachment history; surfaces need reviewed masks.':tab==='founders'?'Authored browser choreography. The new founders and blends are not installed native recipes. Cosmetic blends do not grant reactions.':'Art preview on original room and mannequin illustrations. Native integration and gameplay acceptance remain separate.';
 $('#motion-note').textContent=tab==='identity'?'Toggle the opposing build and grayscale. Quiet layers must retain shape identity; the live fighter stays strongest.':tab==='founders'?'Scrub the full cycle. Blend endpoints are parent-only; the midpoint preserves both shapes. Reduced motion keeps a stable composition.':'Directional silhouettes supplement color. Labels and numbers remain runtime text; examples do not change game state.';
 updateMode();draw();}
function updateMode(){if(tab!=='founders')return;let mode=select('#mode');$('#parentA').closest('.control').hidden=mode==='reaction';$('#parentB').closest('.control').hidden=mode!=='blend';$('#mix').closest('.control').hidden=mode!=='blend';$('#reaction').closest('.control').hidden=mode!=='reaction';}
function library(){let group=select('#group');$('#asset-grid').innerHTML='';D.assets.filter(a=>group==='all'||a.group===group).forEach(a=>{let el=document.createElement('article');el.className='asset';let im=document.createElement('img');im.src=a.file;im.alt=a.name;el.append(im);let h=document.createElement('h3');h.textContent=a.name;el.append(h);let tag=document.createElement('span');tag.textContent=a.group.toUpperCase()+' / '+a.size[0]+'px / '+a.format;el.append(tag);let p=document.createElement('p');p.textContent=a.usage;el.append(p);$('#asset-grid').append(el);});}
async function init(){
 Object.entries(D.families).forEach(([key,f])=>$('#family').add(new Option(f.name,key)));
 Object.entries(D.founders).forEach(([key,f])=>{$('#parentA').add(new Option(f.title,key));$('#parentB').add(new Option(f.title,key));});$('#parentB').value='GlacialShatter';
 Object.entries(D.reactions).forEach(([key,r])=>$('#reaction').add(new Option(r.title,key)));
 [...new Set(D.assets.map(a=>a.group))].forEach(k=>$('#group').add(new Option(k,k)));
 D.blends.forEach(b=>{let btn=document.createElement('button');btn.textContent=b.parents.map(k=>D.founders[k].title).join(' × ');btn.onclick=()=>{$('#mode').value='blend';$('#parentA').value=b.parents[0];$('#parentB').value=b.parents[1];$('#mix').value=50;$('#mix-value').value='50%';updateMode();draw();};$('#blend-strip').append(btn);});
 await Promise.all(D.assets.map(a=>new Promise((resolve,reject)=>{let im=new Image();im.onload=()=>{images[a.name]=im;resolve();};im.onerror=()=>reject(new Error('Missing asset '+a.file));im.src=a.file;})));
 await document.fonts.ready;
 document.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>{setTab(b.dataset.tab);history.replaceState(null,'','#'+tab);});
 document.querySelectorAll('[data-dir]').forEach(b=>b.onclick=()=>choose(b.dataset.dir));
 document.querySelectorAll('select,input[type=checkbox]').forEach(el=>el.addEventListener('change',()=>{if(el.id==='vision'){C.style.filter={normal:'none',gray:'grayscale(1)',protan:'url(#protan)',deutan:'url(#deutan)'}[el.value];}updateMode();draw();}));
 $('#group').onchange=library;$('#mix').oninput=()=>{$('#mix-value').value=select('#mix')+'%';draw();};
 $('#scrub').oninput=()=>{playing=false;time=+select('#scrub');$('#play').textContent='Play';draw();};
 $('#play').onclick=()=>{playing=!playing;$('#play').textContent=playing?'Pause':'Play';};$('#replay').onclick=()=>{time=0;playing=true;$('#play').textContent='Pause';};
 document.addEventListener('keydown',e=>{if(['INPUT','SELECT','TEXTAREA'].includes(e.target.tagName)||e.repeat)return;if(tab==='combat'&&e.key.startsWith('Arrow')){e.preventDefault();choose({ArrowLeft:'left',ArrowRight:'right',ArrowDown:'down',ArrowUp:'up'}[e.key]);}});
 if(matchMedia('(prefers-reduced-motion: reduce)').matches)$('#reduced').checked=true;
 library();setTab(['combat','identity','founders','world','library'].includes(location.hash.slice(1))?location.hash.slice(1):'combat');
 window.review={setTab,draw,setTime:v=>{time=v;playing=false;$('#play').textContent='Play';draw();},getNode:()=>node,ready:true};
 function tick(now){if(playing&&last&&!document.hidden){time=(time+Math.min(now-last,60))%4000;}last=now;if(tab!=='library')draw();requestAnimationFrame(tick);}requestAnimationFrame(tick);
}
init().catch(e=>{$('#annotation').textContent=e.message;console.error(e);});
