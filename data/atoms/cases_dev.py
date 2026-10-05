# (category, lang, text) — authored by the system author; annotated independently by 2 labelers (see data/atoms/README.md)
CASES = [
# simple actions
("action","es","Resume el informe."),("action","en","Translate the contract."),("action","pt","Apague o arquivo."),("action","es","Elimina el registro duplicado."),
("action","en","Send the invoice to the customer."),("action","pt","Atualize o relatório."),("action","es","Verifica la factura."),("action","en","Archive the old tickets."),
("action","es","Cancela el pedido."),("action","en","Call the employee."),("action","pt","Imprima o documento."),("action","en","Review the contract."),
("action","es","Firma el contrato."),("action","en","Schedule a meeting."),("action","pt","Copie o arquivo."),
# entities + properties
("entity","es","Envía los correos pendientes."),("entity","en","Delete the empty files."),("entity","pt","Revise os contratos assinados."),("entity","es","Archiva las facturas pagadas."),
("entity","en","Summarize the confidential documents."),("entity","es","Revisa los pedidos urgentes."),("entity","en","Send the report to Maria Lopez."),("entity","pt","Envie a fatura para o cliente."),
("entity","es","Borra la contraseña antigua."),("entity","en","Publish the new page."),("entity","es","Traduce el texto oficial."),("entity","en","Copy the internal records."),
("entity","pt","Cancele os pedidos pendentes."),("entity","en","Delete the invoice line."),("entity","es","Analiza la imagen externa."),
# quantities
("quantity","es","Resume el informe en máximo 150 palabras."),("quantity","en","Summarize the report in no more than 150 words."),("quantity","pt","Resuma o relatório em no máximo 150 palavras."),
("quantity","es","Resume el informe en máximo 300 palabras."),("quantity","en","Write exactly 10 sentences."),("quantity","es","Escribe al menos 10 frases."),
("quantity","en","Write at most 10 sentences."),("quantity","pt","Escreva aproximadamente 10 frases."),("quantity","en","Send more than 5 emails."),("quantity","es","Envía menos de 5 correos."),
("quantity","en","Keep the summary under 200 characters."),("quantity","pt","Mantenha o resumo com no mínimo 3 parágrafos."),("quantity","es","Elimina exactamente 3 archivos."),
("quantity","en","Review at least 2 contracts."),("quantity","es","Resume el texto en una página."),("quantity","pt","Envie no máximo 2 mensagens."),("quantity","en","Delete roughly 20 records."),
("quantity","es","Responde en 3 líneas."),("quantity","en","Write a summary of up to 5 bullet points."),("quantity","es","Llama a los clientes en menos de 2 horas."),
# constraints / format
("format","es","Exporta el informe en PDF."),("format","en","Send the report as a PDF."),("format","pt","Salve a tabela em CSV."),("format","en","Summarize the document in JSON."),
("format","es","Genera una tabla en Excel."),("format","en","Write the summary in Markdown with at most 100 words."),("format","pt","Envie o relatório em PDF para a Ana."),
("format","es","Guarda la factura en HTML."),("format","en","Translate the text and send it as a PDF."),("format","es","Resume el documento en máximo 50 palabras y envíalo en PDF."),
# negation / modality
("negation","es","Usa fuentes oficiales."),("negation","es","No uses fuentes oficiales."),("negation","en","Do not delete the files."),("negation","pt","Não envie a fatura."),
("negation","en","Never share the password."),("negation","es","Evita enviar correos externos."),("negation","en","You may archive the old records."),("negation","pt","Você pode copiar o arquivo."),
("negation","en","You should review the contract."),("negation","es","No hace falta firmar el contrato."),("negation","en","Avoid deleting the backups."),("negation","es","No dejes de verificar la factura."),
("negation","pt","É proibido apagar os registros."),("negation","en","Do not send the report to external users."),("negation","es","No envíes nada a nadie."),
# conditions
("condition","es","Si el archivo está vacío, solicita otro."),("condition","es","Solicita otro archivo y comprueba si está vacío."),("condition","en","If the invoice is paid, archive it."),
("condition","pt","Se o arquivo estiver vazio, apague-o."),("condition","en","Delete the file only if it is empty."),("condition","en","Delete the file unless it is signed."),
("condition","es","Envía el informe solo si está firmado."),("condition","en","If the order is urgent, call the customer."),("condition","pt","Se o contrato não estiver assinado, envie-o."),
("condition","en","If the file is not empty, send it to Ana."),("condition","es","Si el pedido está pendiente, cancélalo."),("condition","en","Archive the ticket if it is paid."),
("condition","es","Borra el registro a menos que esté firmado."),("condition","en","Send the report if it is signed and not confidential."),("condition","pt","Cancele o pedido se estiver pendente."),
# temporal
("time","es","Envía el informe antes del viernes."),("time","es","Envía el informe el viernes."),("time","es","Envía el informe después del viernes."),
("time","en","Send the report before Friday."),("time","en","Send the report on Friday."),("time","en","Send the report after Friday."),("time","en","Send the report by Friday."),
("time","pt","Envie o relatório até sexta."),("time","es","Envía el informe hasta el viernes."),("time","en","Delete the files today."),("time","es","Llama al cliente mañana."),
("time","en","Review the contract within 24 hours."),("time","pt","Cancele o pedido amanhã."),("time","es","Revisa el contrato desde el lunes."),("time","en","Send the invoice every Monday."),
# references
("reference","es","Resume el informe y envíalo a Ana."),("reference","en","Review the contract and sign it."),("reference","pt","Copie o arquivo e apague-o."),
("reference","es","Elimina el archivo y solicita otro."),("reference","en","Translate the text and send it as a PDF to the customer."),("reference","es","Revisa las facturas y archívalas."),
("reference","en","Delete the file and request another one."),("reference","pt","Abra o relatório e verifique-o."),
# scope / exception
("scope","es","Resume todos los documentos excepto los confidenciales."),("scope","es","Resume todos los documentos confidenciales."),("scope","en","Summarize all documents except the confidential ones."),
("scope","en","Summarize only the confidential documents."),("scope","pt","Resuma todos os documentos exceto os confidenciais."),("scope","es","Elimina todos los archivos excepto los firmados."),
("scope","en","Send the report to all customers except the internal ones."),("scope","es","Envía el informe a algunos clientes."),("scope","en","Delete each invoice that is paid."),
("scope","pt","Envie a fatura a cada cliente."),("scope","en","Do not send the report to any customer."),("scope","es","Archiva solo las facturas pagadas."),
("scope","en","Review every contract except the signed ones."),("scope","pt","Cancele todos os pedidos exceto os urgentes."),("scope","en","Copy none of the confidential files."),
# composition / sequence
("sequence","en","First review the contract, then sign it."),("sequence","es","Revisa el contrato y luego fírmalo."),("sequence","pt","Primeiro revise o contrato, depois assine."),
("sequence","en","Translate the report and send it to Ana."),("sequence","es","Antes de enviar el informe, verifícalo."),("sequence","en","After deleting the files, notify the customer."),
("sequence","es","Resume el informe y traduce el contrato."),("sequence","en","Archive the old tickets and delete the duplicate records."),
("sequence","pt","Verifique a fatura, depois envie ao cliente."),("sequence","en","Review the contract in at most 2 hours and then sign it before Friday."),
# ambiguity / open vocabulary
("open","es","Reconcilia las cuentas del trimestre."),("open","en","Proofread the newsletter draft."),("open","en","Escalate the complaint to the manager."),
("open","pt","Reembolse o cliente."),("open","es","Pon en cuarentena los archivos sospechosos."),("open","en","Rotate the API keys."),("open","es","Haz algo con el informe."),
("open","en","Handle the pending orders."),("open","es","Evita borrar los respaldos pero no los copies."),("open","en","Send it to the usual people."),
]
