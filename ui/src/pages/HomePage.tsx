import { useNavigate } from 'react-router-dom'
import { HomeHeader } from '../components/HomeHeader'
import { Footer } from '../components/Footer'
import { Button } from '../components/ui/button'
import { Badge } from '../components/ui/badge'
import { SUPPORTED_BANKS } from '../constants/banks'
import {
  Zap,
  FileSpreadsheet,
  Eye,
  Upload,
  Cpu,
  Download,
  Shield,
  CheckCircle,
  Building2,
  ArrowRight,
  Sparkles
} from 'lucide-react'

export function HomePage() {
  const navigate = useNavigate()

  const features = [
    {
      icon: Building2,
      title: 'Multi-Bank Support',
      description: '6 major Indian banks supported with intelligent format detection',
      gradient: 'from-purple-500 to-pink-500'
    },
    {
      icon: Zap,
      title: 'Real-time Processing',
      description: 'Instant extraction with live status tracking and progress updates',
      gradient: 'from-blue-500 to-cyan-500'
    },
    {
      icon: FileSpreadsheet,
      title: 'Excel Export',
      description: 'Download formatted transaction data ready for analysis',
      gradient: 'from-green-500 to-emerald-500'
    },
    {
      icon: Eye,
      title: 'PDF Viewer',
      description: 'Side-by-side viewing with synchronized transaction display',
      gradient: 'from-orange-500 to-red-500'
    }
  ]

  const steps = [
    {
      icon: Upload,
      title: 'Upload',
      description: 'Drag & drop your bank statement PDF',
      color: 'text-purple-600'
    },
    {
      icon: Cpu,
      title: 'Process',
      description: 'Intelligent extraction of all transactions',
      color: 'text-blue-600'
    },
    {
      icon: Download,
      title: 'Download',
      description: 'Get Excel file or view online',
      color: 'text-green-600'
    }
  ]

  const trustIndicators = [
    {
      icon: Shield,
      title: 'Secure',
      description: 'Encrypted processing, no data retention',
      color: 'text-green-600'
    },
    {
      icon: Zap,
      title: 'Fast',
      description: 'Average processing time < 30 seconds',
      color: 'text-yellow-600'
    },
    {
      icon: CheckCircle,
      title: 'Accurate',
      description: 'Pattern-based extraction technology',
      color: 'text-blue-600'
    }
  ]

  const scrollToSection = (id: string) => {
    const element = document.getElementById(id)
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' })
    } else {
      console.warn(`Element with id "${id}" not found for scrolling`)
    }
  }

  return (
    <div className="min-h-screen bg-background">
      <HomeHeader />

      {/* Hero Section */}
      <section className="relative pt-32 pb-20 px-6 overflow-hidden">
        {/* Animated Background */}
        <div className="absolute inset-0 bg-gradient-to-br from-purple-600/10 via-blue-600/10 to-pink-600/10 -z-10" />
        <div className="absolute inset-0 hero-pattern -z-10 opacity-30" />

        <div className="max-w-7xl mx-auto text-center">
          {/* Badge */}
          <Badge variant="secondary" className="mb-6 px-4 py-2 bg-purple-100 text-purple-700 border-purple-200">
            <Sparkles className="w-4 h-4 mr-2 inline" />
            Intelligent Document Processing
          </Badge>

          {/* Main Headline */}
          <h1 className="text-5xl md:text-7xl font-bold text-foreground mb-6 leading-tight">
            Transform Bank Statements
            <br />
            into <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-600 to-blue-600">
              Structured Data
            </span>
          </h1>

          {/* Subheadline */}
          <p className="text-xl md:text-2xl text-muted-foreground mb-10 max-w-3xl mx-auto">
            Intelligent Document Processing for 6 Major Indian Banks
            <span className="block mt-2 text-lg">Real-time Extraction • Password Support • Excel Export</span>
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Button
              size="lg"
              className="bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white text-lg px-8 py-6 h-auto font-semibold"
              onClick={() => navigate('/dashboard')}
            >
              Get Started Free
              <ArrowRight className="w-5 h-5 ml-2" />
            </Button>
            <Button
              size="lg"
              variant="outline"
              className="text-lg px-8 py-6 h-auto font-semibold border-2"
              onClick={() => scrollToSection('how-it-works')}
            >
              See How It Works
            </Button>
          </div>

          {/* Trust Badge */}
          <p className="mt-8 text-sm text-muted-foreground">
            No signup required • Free to use • Secure processing
          </p>
        </div>
      </section>

      {/* Supported Banks Section */}
      <section className="py-20 px-6 bg-muted/30">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-4xl font-bold text-foreground mb-4">
              Trusted by users of India's leading banks
            </h2>
            <p className="text-lg text-muted-foreground">
              Supporting 6 major banks with more coming soon
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {SUPPORTED_BANKS.map((bank) => (
              <div
                key={bank.id}
                className="group relative bg-card border border-border rounded-xl p-6 hover:shadow-lg transition-all duration-300 hover:-translate-y-1"
              >
                <div className="flex items-center gap-4">
                  <div className={`w-12 h-12 rounded-lg bg-gradient-to-br ${bank.color} flex items-center justify-center text-white font-bold text-lg`}>
                    {bank.id.slice(0, 2)}
                  </div>
                  <div>
                    <h3 className="font-semibold text-foreground">{bank.name}</h3>
                    <p className="text-sm text-muted-foreground">Supported</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-foreground mb-4">
              Powerful Features for Modern Banking
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Everything you need to process bank statements efficiently and accurately
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {features.map((feature, index) => (
              <div
                key={index}
                className="group relative bg-card/50 backdrop-blur-sm border border-border rounded-2xl p-6 hover:shadow-xl transition-all duration-300 hover:-translate-y-2 glass-card"
              >
                <div className={`w-14 h-14 rounded-xl bg-gradient-to-br ${feature.gradient} flex items-center justify-center mb-4 group-hover:scale-110 transition-transform`}>
                  <feature.icon className="w-7 h-7 text-white" />
                </div>
                <h3 className="text-xl font-semibold text-foreground mb-2">
                  {feature.title}
                </h3>
                <p className="text-muted-foreground">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section id="how-it-works" className="py-20 px-6 bg-muted/30">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-foreground mb-4">
              How It Works
            </h2>
            <p className="text-lg text-muted-foreground">
              Three simple steps to extract your bank statement data
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 relative">
            {/* Connecting Line */}
            <div className="hidden md:block absolute top-16 left-1/6 right-1/6 h-1 bg-gradient-to-r from-purple-600 via-blue-600 to-green-600 -z-10" />

            {steps.map((step, index) => (
              <div key={index} className="relative flex flex-col items-center text-center">
                <div className={`w-20 h-20 rounded-2xl bg-gradient-to-br ${
                  index === 0 ? 'from-purple-500 to-purple-700' :
                  index === 1 ? 'from-blue-500 to-blue-700' :
                  'from-green-500 to-green-700'
                } flex items-center justify-center mb-6 shadow-lg z-10`}>
                  <step.icon className="w-10 h-10 text-white" />
                </div>
                <h3 className="text-2xl font-bold text-foreground mb-3">
                  {step.title}
                </h3>
                <p className="text-muted-foreground text-lg">
                  {step.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Trust Indicators Section */}
      <section className="py-20 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {trustIndicators.map((indicator, index) => (
              <div key={index} className="flex flex-col items-center text-center p-8 bg-card border border-border rounded-2xl">
                <div className={`w-16 h-16 rounded-full bg-gradient-to-br from-${indicator.color.split('-')[1]}-100 to-${indicator.color.split('-')[1]}-200 flex items-center justify-center mb-4`}>
                  <indicator.icon className={`w-8 h-8 ${indicator.color}`} />
                </div>
                <h3 className="text-2xl font-bold text-foreground mb-2">
                  {indicator.title}
                </h3>
                <p className="text-muted-foreground">
                  {indicator.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Final CTA Section */}
      <section className="py-20 px-6 bg-gradient-to-br from-purple-600/10 via-blue-600/10 to-pink-600/10">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-4xl md:text-5xl font-bold text-foreground mb-6">
            Ready to automate your bank statement processing?
          </h2>
          <p className="text-xl text-muted-foreground mb-10">
            Start processing your statements in seconds. No signup required.
          </p>
          <Button
            size="lg"
            className="bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white text-xl px-12 py-7 h-auto font-semibold"
            onClick={() => navigate('/dashboard')}
          >
            Start Processing Now
            <ArrowRight className="w-6 h-6 ml-2" />
          </Button>
          <p className="mt-6 text-sm text-muted-foreground">
            Free to use • No credit card required • Instant access
          </p>
        </div>
      </section>

      <Footer />
    </div>
  )
}