const form=document.getElementById('form');
const err=document.getElementById('error');
const submit=document.getElementById('submit');
const quota=document.getElementById('quota');
const success=document.getElementById('success');
const another=document.getElementById('another');
function fail(message){err.textContent=message;err.hidden=false;}
form.addEventListener('submit',async e=>{
 e.preventDefault();err.hidden=true;
 const data=Object.fromEntries(new FormData(form).entries());
 if(!data.nombres.trim() || !data.apellidos.trim()){fail('Completa nombres y apellidos.');return;}
 if(data.telefono.replace(/\D/g,'').length!==10){fail('Tu teléfono debe contener 10 dígitos.');return;}
 if(!data.calle.trim() || !data.numero_casa.trim() || !data.colonia.trim()){fail('Completa calle, número de casa y colonia.');return;}
 submit.disabled=true;submit.textContent='GENERANDO BOLETO...';
 try{
  const response=await fetch('/api/registro',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  const result=await response.json();
  if(!response.ok)throw new Error(result.error||'No fue posible completar el registro.');
  document.getElementById('success-name').textContent=`Boleto de ${result.nombre}`;
  document.getElementById('download').href=result.boleto_url;
  const ticket=document.getElementById('ticket-result');ticket.src=result.boleto_url;ticket.hidden=false;
  quota.innerHTML=`Te quedan <b>${result.restantes}</b> de 3 registros en este dispositivo.`;
  form.hidden=true;success.hidden=false;success.scrollIntoView({behavior:'smooth',block:'center'});
  another.hidden=result.restantes<=0;
 }catch(ex){fail(ex.message)}finally{submit.disabled=false;submit.innerHTML='GENERAR MI BOLETO <span>➜</span>';}
});
another.addEventListener('click',()=>{form.reset();form.hidden=false;success.hidden=true;err.hidden=true;document.getElementById('nombres').focus()});
