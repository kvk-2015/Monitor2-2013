var WshShell = new ActiveXObject("WScript.Shell"), fso = new ActiveXObject("Scripting.FileSystemObject");
var sArgs = "", Args = WScript.Arguments.Unnamed, firstRun = true, db2ScriptName;

for(var i=0; i<Args.length; i++)sArgs += " " + Args.item(i);
if(fso.GetFileName(WScript.FullName).toLowerCase()=="wscript.exe"){
	WshShell.Run("cmd /c cscript //NoLogo " + WScript.ScriptFullName + " " + sArgs,1);
    WScript.Quit(0);
}

var BaseName = Args.Item(0);
var Duaration =  Args.Item(1);

var oExec = WshShell.Exec('%comspec% /k');
with(oExec.StdIn){
    WriteLine("db2 connect to " + BaseName);
    var scriptFolder = fso.GetFolder(fso.GetFile(WScript.ScriptFullName).ParentFolder);
    var db2Script = new Enumerator(scriptFolder.files);
    for(;!db2Script.atEnd();db2Script.moveNext()){
        if(/^\d+[a-z]*\..+\.sql$/.test(db2ScriptName=db2Script.item().name)){
            WriteLine('@echo ' + db2ScriptName);
            WriteLine('db2 -tvf "' + db2ScriptName + '"');
            if(firstRun){WriteLine('@echo Wait ' + Duaration + ' minute(s)...'); wait(Duaration*60); firstRun = false;}
        }
    }
    WriteLine("db2 connect reset");
    WriteLine("exit");
}
with(fso.CreateTextFile(WScript.ScriptFullName.replace(/\.js/i, ".txt"), true)){
    while(!oExec.Status || !oExec.StdOut.AtEndOfStream){
        currentLine = oExec.StdOut.ReadLine();
        if(!/^db2|>db2|^with|^SQL0204N|^drop|^declare|^insert|^является|^было|ID авторизации|>@echo|^00\.|exit|записей выбрано.|^\s*$/i.test(currentLine))WriteLine(currentLine);
        if(/записей выбрано./.test(currentLine))WriteLine();
    }
}

function wait(seconds){
    var d = new Date();
    d.setSeconds(d.getSeconds()+seconds);
    d = d.getTime();
    with(Math)while(seconds>0){
        mm = floor(seconds/60);
        ss = ":" + ("0" + (seconds - mm * 60)).slice(-2);
        hh = floor(mm/60);
        mm = ":" + ("0" + (mm - hh * 60)).slice(-2);
        WScript.StdOut.Write("\r" + WScript.ScriptName + ": wait " + hh + mm + ss + "...");
        WScript.Sleep(1000);
        seconds = floor((d-(new Date()).getTime())/1000);
    }
}