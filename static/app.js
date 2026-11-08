let dados = {categorias:[], produtos:[], movimentos:[]};
const $ = id => document.getElementById(id);
const esc = texto => String(texto).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function mensagem(texto, erro=false){$('mensagem').textContent=texto;$('mensagem').className=erro?'erro':'';}
function produtos(){
  const lista=dados.produtos.filter(p=>!$('baixo').checked || p.saldo<=p.minimo);
  $('total').textContent=`${dados.produtos.length} produto(s)`;
  $('lista-produtos').innerHTML=lista.map(p=>`<tr><td><strong>${esc(p.nome)}</strong><small>${esc(p.codigo)}</small></td><td>${esc(p.categoria)}</td><td>${p.saldo}</td><td>${p.minimo}</td><td><span class="status ${p.saldo<=p.minimo?'low':''}">${p.saldo<=p.minimo?'Repor':'Disponível'}</span></td></tr>`).join('') || '<tr><td colspan="5">Nenhum produto para exibir.</td></tr>';
}
async function carregar(){
  const resposta=await fetch('/api/dados');if(!resposta.ok)throw Error('Falha ao consultar dados.');dados=await resposta.json();
  $('categoria-select').innerHTML='<option value="">Selecione uma categoria</option>'+dados.categorias.map(c=>`<option value="${c.id}">${esc(c.nome)}</option>`).join('');
  $('produto-select').innerHTML='<option value="">Selecione um produto</option>'+dados.produtos.map(p=>`<option value="${p.id}">${esc(p.nome)} | saldo: ${p.saldo}</option>`).join('');
  $('lista-categorias').innerHTML=dados.categorias.map(c=>`<li>${esc(c.nome)}</li>`).join('') || '<li>Cadastre a primeira categoria.</li>';
  $('lista-movimentos').innerHTML=dados.movimentos.map(m=>`<tr><td>#${m.id}<small>${new Date(m.criado_em).toLocaleString('pt-BR')}</small></td><td>${esc(m.produto)}<small>${esc(m.codigo)}</small></td><td>${m.tipo==='ENTRADA'?'Entrada':'Saída'}</td><td>${m.quantidade}</td><td>${esc(m.observacao)||'—'}</td></tr>`).join('') || '<tr><td colspan="5">Nenhuma movimentação registrada.</td></tr>';produtos();
}
document.querySelectorAll('[data-view]').forEach(botao=>botao.addEventListener('click',()=>{
 document.querySelectorAll('.tela').forEach(t=>t.hidden=t.id!==botao.dataset.view);
 document.querySelectorAll('[data-view]').forEach(b=>b.classList.toggle('ativo',b===botao));mensagem('');
}));
$('baixo').addEventListener('change',produtos);
['categorias','produtos','movimentos'].forEach(tipo=>{
 const form=$('form-'+tipo);form.addEventListener('submit',async evento=>{
 evento.preventDefault();const corpo=Object.fromEntries(new FormData(form));
 ['categoria_id','produto_id','minimo','quantidade'].forEach(c=>{if(c in corpo)corpo[c]=Number(corpo[c]);});
 const botao=form.querySelector('button');botao.disabled=true;
 try{const r=await fetch('/api/'+tipo,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(corpo)});const json=await r.json();if(!r.ok)throw Error(json.erro);form.reset();await carregar();mensagem(json.mensagem);}
 catch(e){mensagem(e.message,true);}finally{botao.disabled=false;}
 });
});
carregar().catch(e=>mensagem(e.message,true));
