(async () => {
    const Gio = (await import('gi://Gio')).default;
    const GLib = (await import('gi://GLib')).default;
    const St = (await import('gi://St')).default;
    const Main = await import('resource:///org/gnome/shell/ui/main.js');
    const root = GLib.getenv('GNOME_PERF_ROOT');
    const variant = GLib.getenv('GNOME_PERF_VARIANT');
    const wait = ms => new Promise(resolve => GLib.timeout_add(GLib.PRIORITY_DEFAULT, ms, () => {
        resolve(); return GLib.SOURCE_REMOVE;
    }));
    const checks = [];
    const check = (name, ok, detail = null) => checks.push({name, ok: !!ok, detail});
    Main.welcomeDialog?.close();
    Main.overview.hide();
    await wait(600);
    const procs = [];
    try {
        for (let n = 0; n < 6; n++) {
            const launcher = new Gio.SubprocessLauncher({flags: Gio.SubprocessFlags.STDOUT_SILENCE | Gio.SubprocessFlags.STDERR_SILENCE});
            launcher.setenv('GDK_BACKEND', 'wayland', true);
            procs.push(launcher.spawnv(['python3', root + '/fixture.py', 'bench-' + n]));
        }
        await wait(1400);
        const windows = global.get_window_actors().filter(a => a.metaWindow.get_title().startsWith('Rounded fixture bench-'));
        check('six private windows', windows.length === 6, windows.length);
        for (let n = 0; n < windows.length; n++)
            windows[n].metaWindow.move_frame(false, 150 + n * 80, 100 + n * 35);
        await wait(600);
        const enabled = [...Main.extensionManager._extensions.values()].map(e => ({uuid: e.uuid, state: e.state, errors: e.error ?? null}));
        const cpuTime = () => {
            const [,bytes] = GLib.file_get_contents('/proc/self/stat');
            const fields = new TextDecoder().decode(bytes).split(') ')[1].split(' ');
            return (Number(fields[11]) + Number(fields[12])) * 10;
        };
        const idle = async () => {
            let paints = 0, last = 0;
            const intervals = [];
            const id = global.stage.connect('after-paint', () => {
                paints++;
                const now = GLib.get_monotonic_time();
                if (last) intervals.push((now-last)/1000);
                last = now;
            });
            const start = cpuTime(); await wait(3500);
            global.stage.disconnect(id);
            return {paints, cpuMs: cpuTime()-start, intervals: stats(intervals)};
        };
        function stats(values) {
            if (!values.length) return {count: 0};
            const a = [...values].sort((x,y) => x-y);
            return {count: a.length, median:a[Math.floor(a.length*.5)], p95:a[Math.floor(a.length*.95)],
                max:a.at(-1), mean:a.reduce((s,v)=>s+v,0)/a.length};
        }
        const desktopIdle = await idle();
        const intervals = [], paintCpu = [], timings = [];
        let before = 0, last = 0, started = 0, direction;
        const ids = [[global.stage, global.stage.connect('before-paint', () => before=GLib.get_monotonic_time())],
            [global.stage, global.stage.connect('after-paint', () => {
                const now=GLib.get_monotonic_time();
                if (Main.overview.animationInProgress) {
                    if (last) intervals.push((now-last)/1000);
                    paintCpu.push((now-before)/1000); last=now;
                } else last=0;
            })]];
        for (const signal of ['showing','hiding','shown','hidden'])
            ids.push([Main.overview,Main.overview.connect(signal, () => {
                if (signal==='showing'||signal==='hiding') {started=GLib.get_monotonic_time();direction=signal;}
                else timings.push({direction,ms:(GLib.get_monotonic_time()-started)/1000});
            })]);
        for (let n=0;n<6;n++) {
            Main.overview.show(); await wait(500);
            Main.overview.hide(); await wait(500);
        }
        for (const [a,id] of ids) a.disconnect(id);
        const configuredFactor=St.Settings.get().slow_down_factor;
        // Timing correctness is tested independently from any user's speed preference.
        St.Settings.get().slow_down_factor=1;
        let t=GLib.get_monotonic_time();
        const nativeDuration = await new Promise(resolve => {
            const id=Main.overview.connect('shown',()=>{Main.overview.disconnect(id);resolve((GLib.get_monotonic_time()-t)/1000);});
            Main.overview.show();
        });
        check('native overview duration',nativeDuration>=240&&nativeDuration<350,nativeDuration);
        const overviewIdle=await idle();
        const appDisplay=Main.overview._overview._controls._appDisplay;
        const foldersBefore=appDisplay._folderIcons.map(icon=>({name:icon.name,dialog:!!icon._dialog}));
        if (variant==='optimized')
            check('unopened folders remain lazy',foldersBefore.every(f=>!f.dialog),foldersBefore);
        Main.overview.showApps(); await wait(600);
        const foldersAfter=appDisplay._folderIcons.map(icon=>({name:icon.name,dialog:!!icon._dialog}));
        const folder=appDisplay._folderIcons[0];
        if (folder) {
            folder._ensureFolderDialog();
            check('folder dialog can be created',!!folder._dialog);
            check('folder grid configured',folder.view._grid.layout_manager.columnsPerPage>0);
            folder._dialog.popup(); await wait(500);
            check('folder opens',folder._dialog.visible);
            if (variant!=='none') check('folder blur attached before visible paint',!!folder._dialog.get_effect('appfolder-blur'));
            folder._dialog.popdown(); await wait(500);
        }
        Main.overview.hide(); await wait(500);
        if (variant==='optimized') {
            const cat=Main.panel.statusArea['runcat-indicator'];
            check('RunCat visible animation active',cat.mapped&&cat.animationTimeoutId!==null);
            cat.hide(); await wait(60);
            const sprite=cat.currentSpriteFrame;
            check('RunCat hidden timer paused',cat.animationTimeoutId===null);
            await wait(350);
            check('RunCat hidden sprite stable',cat.currentSpriteFrame===sprite);
            cat.show(); await wait(80);
            check('RunCat animation resumes',cat.animationTimeoutId!==null);
            const monitor=Main.extensionManager.lookup('system-monitor@gnome-shell-extensions.gcampax.github.com').stateObj._indicator;
            check('network monitor polling visible',!!monitor._ulSection._updateId&&!!monitor._dlSection._updateId);
            monitor.hide(); await wait(60);
            check('network monitor polling paused',!monitor._ulSection._updateId&&!monitor._dlSection._updateId);
            monitor.show(); await wait(80);
            check('network monitor resumes',!!monitor._ulSection._updateId&&!!monitor._dlSection._updateId);
            const vitals=Main.panel.statusArea.vitalsMenu;
            const queried=[];
            const sensors=vitals._sensors;
            const saved={};
            sensors._hardware_detected=true;
            for (const name of ['Memory','System','Battery','Processor','Network','Storage','Gpu']) {
                const key='_query'+name;
                saved[key]=sensors[key];
                sensors[key]=()=>queried.push(name);
            }
            try {
                sensors.query(()=>{},2,new Set(['__temperature_avg__','_gpu#1_temperature_','_gpu#1_utilization_']));
                check('unpinned absolute sensors skipped',!queried.includes('Memory')&&!queried.includes('Battery')&&!queried.includes('System'),queried.slice());
                check('rate baselines maintained',queried.includes('Processor')&&queried.includes('Network')&&queried.includes('Storage'));
                queried.length=0;
                sensors.query(()=>{},2,null);
                check('menu queries all enabled categories',queried.includes('Memory')&&queried.includes('Battery')&&queried.includes('System'),queried.slice());
            } finally {for (const [key,value] of Object.entries(saved)) sensors[key]=value;}
            const Files=await import(vitals._extensionObject.dir.get_child('helpers').get_child('file.js').get_uri());
            const originalRead=Files.File.prototype.read;
            const readPaths=[];
            Files.File.prototype.read=function(...args){readPaths.push(this.file.get_path());return originalRead.apply(this,args);};
            const queryGpu=sensors._queryGpu;
            sensors._queryGpu=()=>{};
            vitals._destroyTimer();
            try {
                sensors.query(()=>{},2,new Set(['__temperature_avg__','_gpu#1_temperature_','_gpu#1_utilization_']));
                await wait(180);
                const closed=readPaths.slice(); readPaths.length=0;
                sensors.query(()=>{},2,null); await wait(180);
                const open=readPaths.slice();
                check('closed menu skips CPU frequency reads',!closed.includes('/proc/cpuinfo')&&open.includes('/proc/cpuinfo'));
                check('closed menu retains CPU/storage baselines',closed.includes('/proc/stat')&&closed.includes('/proc/diskstats'));
                check('closed menu avoids unused battery and memory reads',!closed.includes('/proc/meminfo')&&!closed.some(p=>p?.includes('/power_supply/')));
                check('fewer closed menu sensor reads',closed.length<open.length,{closed:closed.length,open:open.length});
            } finally {
                Files.File.prototype.read=originalRead;
                sensors._queryGpu=queryGpu;
                vitals._initializeTimer();
            }
            vitals.menu.open(); await wait(2300);
            check('Vitals full menu remains usable',vitals.menu.isOpen&&Object.keys(vitals._sensorMenuItems).length>20,Object.keys(vitals._sensorMenuItems).length);
            vitals.menu.close(); await wait(150);
            const tuner=Main.extensionManager.lookup('app-grid-tuner@m-lab').stateObj.appGridTuner;
            let redisplays=0;
            const redisplay=folder.view._redisplay;
            folder.view._redisplay=function(...args){redisplays++;return redisplay.apply(this,args);};
            tuner.applyFolderViewChanges();
            tuner.applyFolderViewChanges();
            check('unchanged folder redisplay cached',redisplays===0,redisplays);
            folder.view._redisplay=redisplay;
            const Bms=Main.extensionManager.lookup('blur-my-shell@aunetx').stateObj;
            const {AppFolderDialog}=await import('resource:///org/gnome/shell/ui/appDisplay.js');
            const originalPopup=Bms._appfolder_blur._popupHook.original;
            Bms._appfolder_blur.disable();
            check('lazy blur hook restored on disable',AppFolderDialog.prototype.popup===originalPopup);
            check('folder blur removed on disable',!folder._dialog.get_effect('appfolder-blur'));
            Bms._appfolder_blur.enable();
            check('lazy blur hook returns on enable',AppFolderDialog.prototype.popup!==originalPopup);
            const gridExtension=Main.extensionManager.lookup('app-grid-tuner@m-lab').stateObj;
            const originalEnsure=tuner.originalStates.get(folder).ensureFolderDialog;
            gridExtension.disable();
            check('folder creation wrapper restored on disable',folder._ensureFolderDialog===originalEnsure);
            gridExtension.enable();
            check('folder tuner can re-enable',!!gridExtension.appGridTuner);
        }
        const result={variant,limitation:'Private headless 2560x1440@165; not physical presentation FPS; GSConnect intentionally excluded',
            enabled,checks,configuredFactor,nativeDuration,desktopIdle,overviewIdle,foldersBefore,foldersAfter,
            overview:{intervals:stats(intervals),paintCpu:stats(paintCpu),timings},
            paintFlags:global._bmsPaintFlags??null};
        GLib.file_set_contents(root+'/'+variant+'-results.json',JSON.stringify(result,null,2));
        return JSON.stringify({variant,checks,overview:result.overview,desktopIdle,overviewIdle,foldersBefore});
    } finally { for (const p of procs) p.force_exit(); }
})()
