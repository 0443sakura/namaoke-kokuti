/**
 * 生バンドカラオケの告知が出ていないときに、Gmail でお知らせします。
 *
 * Google Apps Script（script.google.com）に貼って使います。
 * GitHub の定時実行とも、さくらさんの Mac とも関係なく、Google の時計で動きます。
 * 2026-09-25 に、GitHub の定時実行が動かず、Mac も開いていないと気付けない、
 * という話から作りました。
 *
 * 見るのは GitHub に残る記録だけです（リポジトリが公開なので、鍵は要りません）。
 *   木 18時   … 下書き drafts/次の水曜.json ができているか
 *   金 15時   … 投稿の記録 logs/次の水曜.json に成功があるか
 *   土 10時   … 同じ（金曜に気付けなかったときの念押し）
 *   水  9時   … 当日の記録 logs/今日-today.json に成功があるか
 *
 * 使い方：貼ったあと、上の関数えらびで setup を選んで ▶実行 を1回だけ押します。
 * 試しにメールを送るときは testMail を実行します。
 */

const REPO = '0443sakura/namaoke-kokuti';
const TZ = 'Asia/Tokyo';

function setup() {
  ScriptApp.getProjectTriggers().forEach(t => ScriptApp.deleteTrigger(t));
  const at = (day, hour) => ScriptApp.newTrigger('check').timeBased()
    .onWeekDay(day).atHour(hour).inTimezone(TZ).create();
  at(ScriptApp.WeekDay.THURSDAY, 18);
  at(ScriptApp.WeekDay.FRIDAY, 15);
  at(ScriptApp.WeekDay.SATURDAY, 10);
  at(ScriptApp.WeekDay.WEDNESDAY, 9);
}

function check() {
  const now = new Date();
  const wd = Number(Utilities.formatDate(now, TZ, 'u')) % 7;  // 0=日 … 3=水 … 6=土
  const today = Utilities.formatDate(now, TZ, 'yyyy-MM-dd');
  const nextWed = Utilities.formatDate(
    new Date(now.getTime() + ((3 - wd + 7) % 7 || 7) * 86400000), TZ, 'yyyy-MM-dd');

  if (wd === 4) {
    if (!fetch_('drafts/' + nextWed + '.json')) {
      mail_(label_(nextWed) + ' の下書きができていません',
        'いつもなら木曜のうちに、次回の告知の下書きができています。\n' +
        'Mac を開いてください。開けば自動で作り始めます。\n' +
        'そのあと Claude に「下書きを見せて」と話しかけてください。');
    }
  } else if (wd === 5 || wd === 6) {
    if (!posted_('logs/' + nextWed + '.json')) {
      mail_(label_(nextWed) + ' の告知が、まだ Instagram に出ていません',
        'GitHub の予約が動いていないか、承認（approve）がまだのようです。\n\n' +
        '・Mac を開いてください。開けば自動で出します（承認ずみなら1〜2分で出ます）\n' +
        '・それでも出ないときは、Claude に「告知が出ていない」と話しかけてください');
    }
  } else if (wd === 3) {
    if (!posted_('logs/' + today + '-today.json')) {
      mail_('本日 ' + label_(today) + ' のストーリーが、まだ出ていません',
        '当日の朝のストーリーが出ていません。\n\n' +
        '・Mac を開いてください。今日（水曜）のうちなら、開けば自動で出ます\n' +
        '・それでも出ないときは、Claude に「当日のストーリーが出ていない」と話しかけてください');
    }
  }
}

/** 試しにメールを1通送ります（届くかどうかの確認用） */
function testMail() {
  mail_('（試し）告知の見張りを始めました',
    'このメールが届けば、通知の準備はできています。\n' +
    '告知が出ていないときだけ、このアドレスにお知らせが届きます。');
}

// GitHub にそのファイルがあれば中身を、無ければ null を返します。
function fetch_(path) {
  const res = UrlFetchApp.fetch(
    'https://api.github.com/repos/' + REPO + '/contents/' + encodeURI(path),
    { headers: { Accept: 'application/vnd.github.raw' }, muteHttpExceptions: true });
  if (res.getResponseCode() === 404) return null;
  if (res.getResponseCode() !== 200) {
    throw new Error('GitHub が ' + res.getResponseCode() + ' を返しました');
  }
  return res.getContentText();
}

// 記録があり、1つでも成功していれば true（already_posted.py と同じ考え方）
function posted_(path) {
  const text = fetch_(path);
  if (!text) return false;
  try {
    return JSON.parse(text)['結果'].some(r => r.ok);
  } catch (e) {
    return false;
  }
}

function label_(ymd) {
  const d = new Date(ymd + 'T00:00:00+09:00');
  return Number(ymd.slice(5, 7)) + '/' + Number(ymd.slice(8, 10)) + '（' +
    '日月火水木金土'[Number(Utilities.formatDate(d, TZ, 'u')) % 7] + '）';
}

function mail_(subject, body) {
  MailApp.sendEmail(Session.getEffectiveUser().getEmail(),
    '【生バンドカラオケ】' + subject,
    body + '\n\n' +
    '記録: https://github.com/' + REPO + '/tree/main/logs\n' +
    '（このメールは Google Apps Script の「告知の見張り」から届いています）');
}
