var str, WshShell = new ActiveXObject("WScript.Shell");
var isArial = false, textAreaLength = (isArial ? 57: 157), headLength = 11; // isArial - нужно ли печатать на принтере крупно или только смотреть в Far Manager
var ffProbe = WshShell.ExpandEnvironmentStrings("%FFmpegPath%") + "ffprobe.exe"; tailLength = textAreaLength - headLength; MINIMAL_WORD_LENGTH_AT_END_OF_LINE = 3;
var re = new RegExp("\\s*(.{0," + (tailLength - MINIMAL_WORD_LENGTH_AT_END_OF_LINE) + "}\\S{" + MINIMAL_WORD_LENGTH_AT_END_OF_LINE + "})(?=\\s+|$)","g");
var fso = new ActiveXObject("Scripting.FileSystemObject"), shellApp = new ActiveXObject("Shell.Application"), header;
var s, sum, Arg, Args, startFolders = [], dd = (new Array(isArial ? 91 : textAreaLength + 1)).join("-"), fsp = (new Array(isArial ? 16 : headLength - 1)).join(" ");
var CodePages = [];

with(str = new ActiveXObject("ADODB.Stream")){Type = 2; Mode = 3;}

if(ArgsCount=(Args=WSH.Arguments.Unnamed).Count){
    for(var i=0;i<ArgsCount;i++)if(fso.FolderExists(Args(i)))startFolders.push(fso.GetAbsolutePathName(Args(i)))
}else startFolders = [fso.GetParentFolderName(WSH.ScriptFullName)];

for(var curFolder=0;curFolder<startFolders.length;curFolder++){s = "" ; sum = [0,0,0];
    getInfo(folder=startFolders[curFolder]); normTime(sum); header = "Оглавление " + fso.GetFileName(folder);
    with(fso.CreateTextFile(fso.BuildPath(folder, header + ".txt"), true, true)){
            Write((isArial ? ">>>Arial 16<<<\r\n" : "") + header + " (" + sum.join(":")+ "):" + (s.substr(2,1) == "-" ? "" : "\r\n" + dd) + s);
            Close();
    }
}


function getInfo(folder){
    var sf = new Enumerator(fso.GetFolder(folder).subFolders), list = [], duration = new Array(3);
    for(;!sf.atEnd();sf.moveNext())list.push(sf.item().Name);
    list.sort();
    for(var i=0;i<list.length;i++)
        if(/^(?:\d+[a-z]?)(?:[-,]\d+[a-z]?)*\./.test(list[i]))getInfo(fso.BuildPath(folder, list[i]));
    var cs = "", len = [0,0,0], sFolder = shellApp.NameSpace(folder);
    var fc = new Enumerator(fso.GetFolder(folder).files), objItem;
    list = [];
    for(;!fc.atEnd();fc.moveNext())list.push(fc.item().Name);
    list.sort();
    for(var j=0;j<list.length;j++)
        if(/^(?:avi|mp4|mkv|ts|mov)$/i.test(fso.GetExtensionName(fn=list[j])))
        if(/(\d{1,2}):(\d{2}):(\d{2})/.test(sFolder.GetDetailsOf(objItem=sFolder.ParseName(fn), 27)) ||
            /(?:Длина|Продолжительность):\s(\d{1,2}):(\d{2}):(\d{2})/.test(sFolder.GetDetailsOf(objItem, -1)) || ffget(fso.BuildPath(folder, fn))){
            cs += "\r\n" + ("0" + (duration[0] = RegExp.$1)).slice(-2) + ":" + (duration[1] = RegExp.$2) + ":" + (duration[2] = RegExp.$3) + " | " +
                  splitStrings(fn, true);
            if(!/\.!|^!/.test(fn))for(var i=0;i<3;i++)len[i] += parseInt(duration[i], 10);
        }
    for(i=0;i<3;i++)sum[i] += len[i]; normTime(len); cf = folder.slice(startFolders[curFolder].length).replace(/^\\/,"");
    if(cs)s += "\r\n" + (cf ? splitStrings(cf + " ("+len.join(":") + "):") + "\r\n" : "") + dd + cs + "\r\n" + dd;
}


function splitStrings(inp, isFileName){var out = "", row = 0;
    while(re.exec(inp))out += "\r\n" + (isFileName && row++ ? fsp + "| " + RegExp.$1 : RegExp.$1);
    return out.substr(2);
}


function normTime(len){
    for(var i=2;i;i--){if(len[i]>=60){len[i-1] += Math.floor(len[i]/60); len[i] %= 60} len[i] = ("0" + len[i]).slice(-2)}
}

function ffget(fname){
    var oExec = WshShell.Exec(ffProbe + ' -show_format -pretty "' + fname + '"');
    while(!oExec.Status || !oExec.StdOut.AtEndOfStream){
        if(/duration=(\d{1,2}):(\d{2}):(\d{2})/.test(DosToWin(oExec.StdOut.ReadLine())))return true;
    }
    return false;
}

function DosToWin(dosString){
    function getCodepage(){
        while(!oExec.Status || !oExec.StdOut.AtEndOfStream){
            var new_codepage = oExec.StdOut.ReadAll().replace(/^[\s\S]*\s(\d+)\s*$/, "$1");
        }
        return new_codepage;
    }
    var result;
    if(!CodePages.length){
        var oExec = WshShell.Exec('cmd.exe /c chcp');   DOS_codepage = getCodepage();
        oExec = WshShell.Exec('reg.exe query "HKLM\\SYSTEM\\CurrentControlSet\\Control\\Nls\\CodePage" -v ACP'); Windows_codepage = getCodepage();
        if(DOS_codepage != Windows_codepage)CodePages = ["cp" + DOS_codepage, "Windows-" + Windows_codepage];
    }
    if(!CodePages.length)return dosString;
    with(str){
        Open();
        Charset = CodePages[1];
        WriteText(dosString);
        Position = 0;
        Charset = CodePages[0];
        result = ReadText();
        Close();
    }
    return result;
}