import fs from 'node:fs'
import path from 'node:path'
import {execFileSync} from 'node:child_process'
import {fileURLToPath} from 'node:url'
import {compileApplesoftBasic} from './applebasic.mjs'

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..','..')
const build=path.join(root,'vera','build')
const a2=path.join(root,'vera','src','a2vera')
const cadius=path.join(root,'vera','tools','cadius.exe')
const hdv=path.join(build,'alter-ego-vera.hdv')
const disks=[
  {file:path.join(build,'alter-ego-vera-D1.po'),volume:'ALTER.EGO'},
  {file:path.join(build,'alter-ego-vera-D2.po'),volume:'ALTER.EGO.2'},
]
const bootFiles=['PRODOS','BASIC.SYSTEM','STARTUP','AEMUSIC2','AEMUSIC4',
                 'AE2VERA2','AE2VERA4']
const relative=file=>path.relative(root,file)
const run=(...args)=>execFileSync(cadius,args,{cwd:root,encoding:'utf8'})

if(!fs.existsSync(hdv)) throw new Error('Build the FTM HDV before packing floppies')
const stage=fs.mkdtempSync(path.join(build,'ftm-floppy-stage-'))
try {
  run('EXTRACTVOLUME',relative(hdv),relative(stage))
  const files=fs.readdirSync(path.join(stage,'ALTER.EGO'))
    .filter(file=>file!=='_FileInformation.txt')
  const byName=new Map(files.map(file=>[file.split('#')[0],file]))
  if(byName.size!==40) throw new Error(`Expected 40 FTM files, found ${byName.size}`)
  for(const name of bootFiles) if(!byName.has(name))
    throw new Error(`FTM HDV is missing ${name}`)
  const startup=compileApplesoftBasic(a2,'startup_floppy.bas')
  fs.writeFileSync(path.join(stage,'ALTER.EGO',byName.get('STARTUP')),startup)
  const readyName='D2READY#040000'
  fs.writeFileSync(path.join(stage,'ALTER.EGO',readyName),Buffer.from('ALTER EGO DISK 2\r'))
  byName.set('D2READY',readyName)

  const bootBlocks=fs.readFileSync(path.join(a2,'prodos','boot_blocks.bin'))
  if(bootBlocks.length!==1024) throw new Error('Invalid ProDOS boot block template')
  for(const disk of disks) {
    if(fs.existsSync(disk.file)) fs.unlinkSync(disk.file)
    run('CREATEVOLUME',relative(disk.file),disk.volume,'140KB')
    const data=fs.readFileSync(disk.file)
    bootBlocks.copy(data,0)
    fs.writeFileSync(disk.file,data)
  }
  function add(disk,name) {
    run('ADDFILE',relative(disk.file),`/${disk.volume}`,
        relative(path.join(stage,'ALTER.EGO',byName.get(name))))
  }
  for(const name of bootFiles) add(disks[0],name)
  for(const name of [...byName.keys()].sort())
    if(!bootFiles.includes(name)) add(disks[1],name)

  for(const [index,disk] of disks.entries()) {
    if(fs.statSync(disk.file).size!==140*1024)
      throw new Error(`${disk.file} is not 140 KB`)
    run('CHECKVOLUME',relative(disk.file))
    const catalog=run('CATALOG',relative(disk.file))
    const summary=catalog.match(/Block\s*:\s*280\s+Free\s*:\s*(\d+)\s+File\s*:\s*(\d+)/)
    if(!summary || Number(summary[2])!==(index===0?7:34))
      throw new Error(`Unexpected file catalog on ${disk.volume}`)
    console.log(`${disk.volume}: ${summary[1]} blocks free`)
  }
  console.log(`RESULT: OK - ${disks.map(d=>d.file).join(' + ')}`)
} finally {
  if(!path.resolve(stage).startsWith(path.resolve(build)+path.sep))
    throw new Error('Refusing to remove a temporary directory outside vera/build')
  fs.rmSync(stage,{recursive:true,force:true})
}
