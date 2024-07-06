var str, WshShell = new ActiveXObject("WScript.Shell");
var ffProbe = "D:\\kvk\\Utilities\\ffmpeg-20160401-git-b3eda69-win32-static\\bin\\ffprobe.exe";
var fso = new ActiveXObject("Scripting.FileSystemObject"), shellApp = new ActiveXObject("Shell.Application");
var s, sum, Arg, Args, startFolders = [], dd = (new Array(91)).join("-"), header;

with(str = new ActiveXObject("ADODB.Stream")){Type = 2; Mode = 3;}

if(ArgsCount=(Args=WSH.Arguments.Unnamed).Count){
	for(var i=0;i<ArgsCount;i++)if(fso.FolderExists(Args(i)))startFolders.push(fso.GetAbsolutePathName(Args(i)))
}else startFolders = [fso.GetParentFolderName(WSH.ScriptFullName)];

for(var curFolder=0;curFolder<startFolders.length;curFolder++){s = "" ; sum = [0,0,0];
	getInfo(folder=startFolders[curFolder]); normTime(sum); header = "Оглавление " + fso.GetFileName(folder);
	with(fso.CreateTextFile(fso.BuildPath(folder, header + ".txt"), true, true)){
			Write(">>>Arial 16<<<\r\n" + header + " (" + sum.join(":")+ "):\r\n" + dd + s);
			Close();
	}
}


function getInfo(folder){
	var sf = new Enumerator(fso.GetFolder(folder).subFolders), list = [];
	for(;!sf.atEnd();sf.moveNext())list[list.length] = sf.item().Name;
    list = list.sort();
    for(var i=0;i<list.length;i++)
		if(/^(?:\d+[a-z]?)(?:[-,]\d+[a-z]?)*\./.test(list[i]))getInfo(fso.BuildPath(folder, list[i]));
	var cs = "", len = [0,0,0], sFolder = shellApp.NameSpace(folder);
	var fc = new Enumerator(fso.GetFolder(folder).files);
    list = [];
	for(;!fc.atEnd();fc.moveNext())list[list.length] = fc.item().Name;
    list = list.sort();
    for(var j=0;j<list.length;j++)
        if(/^(?:avi|mp4|mkv|ts)$/i.test(fso.GetExtensionName(fn=list[j])))
		if(/(?:Длина|Продолжительность):\s(\d{1,2}):(\d{2}):(\d{2})/.test(sFolder.GetDetailsOf(sFolder.ParseName(fn), -1)) ||
			(sFolder.GetDetailsOf(null, 27) == "Продолжительность" &&
				/(\d{1,2}):(\d{2}):(\d{2})/.test(sFolder.GetDetailsOf(sFolder.ParseName(fn), 27))) ||
                ffget(fso.BuildPath(folder, fn))){
			cs += "\r\n" + RegExp.$1 + ":" + RegExp.$2 + ":" + RegExp.$3 + " | " + fn;
            if(!/\.!/.test(fn))for(var i=3;i;i--)len[i-1] += parseInt(RegExp["$"+i], 10);
		}
	for(i=0;i<3;i++)sum[i] += len[i]; normTime(len); cf = folder.slice(startFolders[curFolder].length).replace(/^\\/,"");
	if(cs)s += "\r\n" + (cf?splitStrings(cf+" ("+len.join(":")+"):")+"\r\n":"") + dd + cs + "\r\n" + dd;
}


function splitStrings(inp){re=/\s*(.{0,59}\S)(?=\s+|$)/g,out="";
	while(re.exec(inp))out += "\r\n" + RegExp.$1;
	return out.substr(2);
}


function normTime(len){
	for(var i=2;i;i--){if(len[i]>=60){len[i-1] += Math.floor(len[i]/60); len[i] %= 60} len[i] = ("0" + len[i]).slice(-2)}
}

function ffget(fname){
    oExec = WshShell.Exec(ffProbe + ' -show_format -pretty "' + fname + '"');
    while(!oExec.Status || !oExec.StdOut.AtEndOfStream){
        if(/duration=(\d{1,2}):(\d{2}):(\d{2})/.test(DosToWin(oExec.StdOut.ReadLine())))return true;
    }
    return false;
}

function DosToWin(dosString){
    var result;
    with(str){
        Open();
        Charset = "Windows-1251";
        WriteText(dosString);
        Position = 0;
        Charset = "cp866";
        result = ReadText();
        Close();
    }
    return result;
}