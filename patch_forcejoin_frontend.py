with open("templates/index.html", "r", encoding="utf-8") as f:
    content = f.read()

# 1) Add join-gate screen markup right after loadingScreen div
old_loading = '''<div class="loading-screen" id="loadingScreen">
  <div class="loader"></div>
  <div class="loading-text">TRX PRO</div>
</div>'''
new_loading = '''<div class="loading-screen" id="loadingScreen">
  <div class="loader"></div>
  <div class="loading-text">TRX PRO</div>
</div>

<div class="loading-screen hidden" id="joinGateScreen" style="text-align:center;padding:0 24px;">
  <div style="font-size:48px;margin-bottom:16px;">🔒</div>
  <div class="loading-text" style="margin-bottom:16px;">JOIN REQUIRED</div>
  <div style="font-size:13px;color:var(--text-muted);margin-bottom:24px;line-height:1.6;">
    You must join our group before using TRX PRO.
  </div>
  <a id="joinGateLink" href="#" target="_blank" style="text-decoration:none;width:100%;max-width:280px;">
    <div class="action-btn btn-bet" style="margin-bottom:12px;">JOIN GROUP</div>
  </a>
  <div class="action-btn btn-cashout" style="max-width:280px;" onclick="recheckJoin()">I JOINED - CHECK AGAIN</div>
</div>'''
assert old_loading in content, "loadingScreen anchor not found"
content = content.replace(old_loading, new_loading, 1)

# 2) Modify initAuth to handle not_member response
old_initauth = '''    } else {
      showToast(d.error || 'Auth failed', 'error'); document.getElementById('loadingScreen').classList.add('hidden');
    }
  } catch (e) { showToast('Network error', 'error'); console.error(e); document.getElementById('loadingScreen').classList.add('hidden'); }
}'''
new_initauth = '''    } else if (d.error === 'not_member') {
      document.getElementById('loadingScreen').classList.add('hidden');
      document.getElementById('joinGateLink').href = d.join_url || 'https://t.me/botgrups';
      document.getElementById('joinGateScreen').classList.remove('hidden');
    } else {
      showToast(d.error || 'Auth failed', 'error'); document.getElementById('loadingScreen').classList.add('hidden');
    }
  } catch (e) { showToast('Network error', 'error'); console.error(e); document.getElementById('loadingScreen').classList.add('hidden'); }
}

async function recheckJoin() {
  document.getElementById('joinGateScreen').classList.add('hidden');
  document.getElementById('loadingScreen').classList.remove('hidden');
  await initAuth();
}'''
assert old_initauth in content, "initAuth anchor not found"
content = content.replace(old_initauth, new_initauth, 1)

with open("templates/index.html", "w", encoding="utf-8") as f:
    f.write(content)

print("index.html force-join patch applied successfully")
