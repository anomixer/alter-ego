import fs from 'node:fs'
import path from 'node:path'
import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { compileApplesoftBasic } from './applebasic.mjs'
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..','..')
const build=path.join(root,'vera/build')
const ftmBuild=process.argv.includes('--ftm')
const image=path.join(build,ftmBuild?'alter-ego-vera.hdv':'alter-ego-vera-psg.hdv')
const cadius=path.join(root,'vera/tools/cadius.exe')
const prodosDir=path.join(root,'vera/src/a2vera/prodos')
const tmp=path.join(build,'stage'); fs.mkdirSync(tmp,{recursive:true})
const run=(...args)=>execFileSync(cadius,args,{stdio:'inherit'})
// Recreate a compact volume, preserving the verified ProDOS boot loader.
if(fs.existsSync(image)) fs.unlinkSync(image)
run('CREATEVOLUME',image,'ALTER.EGO','800KB')
const disk=fs.readFileSync(image)
const bootBlocks=fs.readFileSync(path.join(prodosDir,'boot_blocks.bin'))
if(bootBlocks.length!==1024) throw new Error('ProDOS boot block template must be exactly 1024 bytes')
bootBlocks.copy(disk,0,0,1024)
fs.writeFileSync(image,disk)
function entries(po){
  const d=fs.readFileSync(po), out=[],seen=new Set(); let blockNo=2
  while(blockNo && !seen.has(blockNo)){
    seen.add(blockNo); const o=blockNo*512, block=d.subarray(o,o+512)
    const next=block[2]|(block[3]<<8)
    for(let slot=(blockNo===2?1:0);slot<13;slot++){
      const at=4+slot*39, st=block[at]>>4, n=block[at]&15
      if(!st||!n) continue
      out.push({name:block.toString('ascii',at+1,at+1+n),dir:st===13})
    }
    blockNo=next
  }
  return out
}
for(const e of entries(image)) if(!['PRODOS','BASIC.SYSTEM'].includes(e.name))
  run(e.dir?'DELETEFOLDER':'DELETEFILE',image,`/ALTER.EGO/${e.name}`)
function add(name,suffix,data){const p=path.join(tmp,name+suffix);fs.writeFileSync(p,data);run('ADDFILE',image,'/ALTER.EGO',p)}
add('PRODOS','#FF0000',fs.readFileSync(path.join(prodosDir,'PRODOS.bin')))
add('BASIC.SYSTEM','#FF0000',fs.readFileSync(path.join(prodosDir,'BASIC.SYSTEM.bin')))
const startup=compileApplesoftBasic(path.join(root,'vera/src/a2vera'),'startup.bas',
  line=>ftmBuild ? line.replace('VERA     PSG VER"','VERA"') : line)
add('STARTUP','#FC0801',startup)
for(const slot of ['2','4']) {
  add(`AEMUSIC${slot}`,'#061000',fs.readFileSync(path.join(build,`AEMUSIC${slot}#061000`)))
  add(`AE2VERA${slot}`,'#062000',fs.readFileSync(path.join(build,`AE2VERA${slot}#062000`)))
}
add('CREDITS','',fs.readFileSync(path.join(build,'credits_map.bin')))
add('CRPAL','',fs.readFileSync(path.join(build,'credits_palette.bin')))
add('ENDING','',fs.readFileSync(path.join(build,'ending_map.bin')))
add('ENDPAL','',fs.readFileSync(path.join(build,'ending_palette.bin')))
add('GOVER','',fs.readFileSync(path.join(build,'gameover_map.bin')))
add('GOPAL','',fs.readFileSync(path.join(build,'gameover_palette.bin')))
add('TILES','',Buffer.concat([
  fs.readFileSync(path.join(build,'title_tiles_4bpp.bin')),
  fs.readFileSync(path.join(build,'title_tiles_alt_4bpp.bin')),
]))
for(let n=0;n<26;n++){
  const id=String(n).padStart(2,'0'),dir=path.join(build,'levels',`LV${id}`)
  const level=Buffer.concat([
    fs.readFileSync(path.join(dir,'level_map_size.bin')),
    fs.readFileSync(path.join(dir,'level_map_rle.bin')),
    fs.readFileSync(path.join(dir,'level_palette.bin')),
    fs.readFileSync(path.join(dir,'level_pause_palette.bin')),
    fs.readFileSync(path.join(dir,'level_entities.bin')),
    fs.readFileSync(path.join(dir,'level_params.bin')),
    fs.readFileSync(path.join(dir,'level_collision.bin')),
  ])
  add(`LV${id}`,'',level)
}
if(!ftmBuild){
  for(const song of ['TITLE','LEVEL1','LEVEL2','LEVEL2ALT','LEVEL3','LEVEL4','LEVEL5','GAMEOVER','CONGRATS','CLEAR'])
    add(`${song}.PSG`,'',fs.readFileSync(path.join(build,'music',`${song}.psg`)))
  const sfxBank=Buffer.alloc(15*384)
  for(let n=0;n<15;n++){
    const clip=fs.readFileSync(path.join(build,'music',`SFX${String(n).padStart(2,'0')}`))
    if(clip.length>384) throw new Error(`SFX${String(n).padStart(2,'0')} exceeds its 384-byte bank slot`)
    clip.copy(sfxBank,n*384)
  }
  add('SFXBANK','',sfxBank)
}
const required=['PRODOS','BASIC.SYSTEM','STARTUP','AEMUSIC2','AE2VERA2','AEMUSIC4','AE2VERA4','CREDITS','CRPAL','ENDING','ENDPAL','GOVER','GOPAL','TILES',
  ...(ftmBuild?[]:['TITLE.PSG','LEVEL1.PSG','GAMEOVER.PSG','LEVEL2.PSG','LEVEL2ALT.PSG','LEVEL3.PSG','LEVEL4.PSG','LEVEL5.PSG','CONGRATS.PSG','CLEAR.PSG','SFXBANK']),
  ...Array.from({length:26},(_,n)=>`LV${String(n).padStart(2,'0')}`)]
const present=new Set(entries(image).map(e=>e.name))
for(const name of required) if(!present.has(name))
  throw new Error(`Disk image is missing required file ${name}`)
if(fs.statSync(image).size!==800*1024) throw new Error('Disk image is not 800 KB')
run('CHECKVOLUME',image)
run('CATALOG',image)
console.log(`RESULT: OK - ${image}`)

