import React, { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';

const FAQ: React.FC = () => {
  const faqs = [
    {
      question: "Quais marcas de elevadores o Elevex atende?",
      answer: "O Elevex possui uma base de dados abrangente que cobre as principais marcas nacionais e importadas, incluindo Otis, Schindler, Thyssenkrupp, Atlas, e muitas outras marcas de inversores genéricos."
    },
    {
      question: "Preciso de internet para usar o app?",
      answer: "Sim, o Elevex utiliza processamento em nuvem para garantir que você tenha acesso às informações mais atualizadas e à nossa inteligência artificial. No entanto, o consumo de dados é otimizado."
    },
    {
      question: "Como funciona o plano 'Empresa' com 5 logins?",
      answer: "O plano Empresa permite criar até 5 perfis de acesso sob uma mesma fatura. Ideal para pequenas conservadoras que querem fornecer a ferramenta para sua equipe técnica."
    },
    {
      question: "O Elevex substitui um curso técnico?",
      answer: "Não. O Elevex é uma ferramenta de suporte à decisão. Ele potencializa o conhecimento do técnico, mas o treinamento fundamental e as normas de segurança são indispensáveis."
    },
    {
      question: "Posso cancelar a minha assinatura quando quiser?",
      answer: "Sim, sem contratos de fidelidade. Você pode cancelar a qualquer momento através das configurações da sua conta."
    },
    {
      question: "O que acontece se eu não encontrar o defeito que procuro?",
      answer: "Nossa IA aprende constantemente. Se um defeito não for encontrado, você pode reportá-lo, e nossa equipe de engenharia analisará para adicionar à base de dados."
    },
  ];

  const [openIndex, setOpenIndex] = useState<number | null>(null);

  return (
    <div id="faq" className="bg-white py-24 relative overflow-hidden">
      {/* Background Elements */}
      <div className="absolute top-0 left-0 w-full h-full pointer-events-none">
        <div className="absolute bottom-0 right-0 w-[800px] h-[400px] bg-gradient-to-tl from-slate-100 to-transparent rounded-tl-full blur-3xl"></div>
      </div>

      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
        <div className="text-center mb-16">
          <h2 className="text-base font-semibold text-blue-600 tracking-wide uppercase mb-3">Dúvidas</h2>
          <h3 className="text-3xl font-extrabold text-slate-900 sm:text-4xl tracking-tight">Perguntas Frequentes</h3>
        </div>
        
        <div className="space-y-4">
          {faqs.map((faq, index) => (
            <div 
              key={index} 
              className={`bg-white border rounded-2xl overflow-hidden transition-all duration-300 ${openIndex === index ? 'border-blue-200 shadow-md shadow-blue-500/5' : 'border-slate-200 hover:border-slate-300 hover:shadow-sm'}`}
            >
              <button
                className="w-full px-6 py-5 text-left flex justify-between items-center focus:outline-none transition-colors"
                onClick={() => setOpenIndex(openIndex === index ? null : index)}
              >
                <span className={`font-semibold pr-4 ${openIndex === index ? 'text-blue-700' : 'text-slate-800'}`}>
                  {faq.question}
                </span>
                <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center transition-colors ${openIndex === index ? 'bg-blue-100 text-blue-600' : 'bg-slate-100 text-slate-400'}`}>
                  {openIndex === index ? (
                    <ChevronUp className="h-5 w-5" />
                  ) : (
                    <ChevronDown className="h-5 w-5" />
                  )}
                </div>
              </button>
              <div 
                className={`px-6 overflow-hidden transition-all duration-300 ease-in-out ${openIndex === index ? 'max-h-40 pb-5 opacity-100' : 'max-h-0 opacity-0'}`}
              >
                <p className="text-slate-600 text-base leading-relaxed border-t border-slate-100 pt-4">{faq.answer}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default FAQ;