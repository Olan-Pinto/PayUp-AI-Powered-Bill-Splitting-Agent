import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { ThemeToggle } from "@/components/ThemeToggle";
import { 
  DollarSign, 
  Download, 
  Home, 
  Users, 
  Receipt, 
  Copy, 
  CheckCircle2,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Eye
} from "lucide-react";
import { API_URL } from '../config';


function Result() {
  const { bill_id } = useParams();
  const navigate = useNavigate();
  const [billData, setBillData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showJSON, setShowJSON] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const fetchBillData = async () => {
      try {
        const response = await axios.get(`${API_URL}/bill/${bill_id}`);
        setBillData(response.data);
        setLoading(false);
      } catch (err) {
        setError(err.response?.data?.error || 'Bill not found');
        setLoading(false);
      }
    };

    fetchBillData();
  }, [bill_id]);

  const downloadBill = async () => {
    try {
      const response = await axios.get(
        `${API_URL}/bill/${bill_id}/download`,
        { responseType: 'blob' }
      );

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `bill_${bill_id}.jpg`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      alert('Download failed');
    }
  };

  const copyBillId = () => {
    navigator.clipboard.writeText(bill_id);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50 dark:from-gray-950 dark:via-gray-900 dark:to-gray-950 flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="h-16 w-16 border-4 border-gray-200 dark:border-gray-700 border-t-indigo-600 dark:border-t-indigo-400 rounded-full animate-spin mx-auto" />
          <div className="space-y-2">
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">
              Loading your bill...
            </h2>
            <p className="text-gray-600 dark:text-gray-400">
              Please wait a moment
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50 dark:from-gray-950 dark:via-gray-900 dark:to-gray-950">
        <nav className="border-b bg-white/50 dark:bg-gray-900/50 backdrop-blur-xl">
          <div className="container mx-auto px-4">
            <div className="flex items-center justify-between h-16">
              <div className="flex items-center gap-2">
                <div className="h-10 w-10 rounded-full bg-gradient-to-br from-indigo-600 to-purple-600 flex items-center justify-center">
                  <DollarSign className="h-6 w-6 text-white" />
                </div>
                <h1 className="text-xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 dark:from-indigo-400 dark:to-purple-400 bg-clip-text text-transparent">
                  PayUp
                </h1>
              </div>
              <ThemeToggle />
            </div>
          </div>
        </nav>
        
        <div className="container mx-auto px-4 py-8 flex items-center justify-center min-h-[calc(100vh-4rem)]">
          <Card className="max-w-md w-full shadow-xl border-0 bg-white/80 dark:bg-gray-900/80 backdrop-blur-xl">
            <CardContent className="pt-6 space-y-4">
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
              <Button onClick={() => navigate('/')} className="w-full" size="lg">
                <Home className="h-5 w-5 mr-2" />
                Back to Home
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  const totalAmount = billData?.split_result?.breakdown?.[0]?.total || 0;
  const numberOfPeople = billData?.split_result?.breakdown?.length || 0;

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50 dark:from-gray-950 dark:via-gray-900 dark:to-gray-950">
      {/* Top Navigation */}
      <nav className="border-b bg-white/50 dark:bg-gray-900/50 backdrop-blur-xl sticky top-0 z-40">
        <div className="container mx-auto px-4">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-2">
              <div className="h-10 w-10 rounded-full bg-gradient-to-br from-indigo-600 to-purple-600 flex items-center justify-center">
                <DollarSign className="h-6 w-6 text-white" />
              </div>
              <h1 className="text-xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 dark:from-indigo-400 dark:to-purple-400 bg-clip-text text-transparent">
                PayUp
              </h1>
            </div>
            <div className="flex items-center gap-2">
              <ThemeToggle />
              <Button 
                onClick={() => navigate('/')} 
                variant="ghost"
                size="sm"
                className="gap-2"
              >
                <Home className="h-4 w-4" />
                <span className="hidden sm:inline">Home</span>
              </Button>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto space-y-6">
          {/* Success Header */}
          <div className="text-center space-y-4">
            <div className="inline-flex h-16 w-16 items-center justify-center rounded-full bg-green-100 dark:bg-green-950 mx-auto animate-scale-in">
              <CheckCircle2 className="h-10 w-10 text-green-600 dark:text-green-400" />
            </div>
            <div className="space-y-2">
              <h1 className="text-3xl md:text-4xl font-bold text-gray-900 dark:text-white">
                Bill Split Successfully!
              </h1>
              <p className="text-gray-600 dark:text-gray-400">
                Here's your detailed breakdown
              </p>
            </div>
            
            {/* Bill ID Badge */}
            <div className="flex items-center justify-center gap-2">
              <Badge 
                variant="secondary" 
                className="text-sm px-4 py-2 font-mono cursor-pointer hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                onClick={copyBillId}
              >
                {copied ? (
                  <>
                    <CheckCircle2 className="h-3 w-3 mr-2" />
                    Copied!
                  </>
                ) : (
                  <>
                    <Copy className="h-3 w-3 mr-2" />
                    {bill_id}
                  </>
                )}
              </Badge>
            </div>
          </div>

          {/* Stats Cards */}
          <div className="grid md:grid-cols-2 gap-4">
            <Card className="shadow-lg border-0 bg-gradient-to-br from-indigo-50 to-purple-50 dark:from-indigo-950/30 dark:to-purple-950/30 backdrop-blur-xl">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600 dark:text-gray-400 font-medium">
                      Per Person
                    </p>
                    <p className="text-3xl font-bold text-gray-900 dark:text-white mt-1">
                      ${totalAmount.toFixed(2)}
                    </p>
                  </div>
                  <div className="h-12 w-12 rounded-full bg-indigo-100 dark:bg-indigo-900 flex items-center justify-center">
                    <DollarSign className="h-6 w-6 text-indigo-600 dark:text-indigo-400" />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="shadow-lg border-0 bg-gradient-to-br from-purple-50 to-pink-50 dark:from-purple-950/30 dark:to-pink-950/30 backdrop-blur-xl">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600 dark:text-gray-400 font-medium">
                      Split Between
                    </p>
                    <p className="text-3xl font-bold text-gray-900 dark:text-white mt-1">
                      {numberOfPeople} {numberOfPeople === 1 ? 'Person' : 'People'}
                    </p>
                  </div>
                  <div className="h-12 w-12 rounded-full bg-purple-100 dark:bg-purple-900 flex items-center justify-center">
                    <Users className="h-6 w-6 text-purple-600 dark:text-purple-400" />
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Bill Image */}
          <Card className="shadow-xl border-0 bg-white/80 dark:bg-gray-900/80 backdrop-blur-xl overflow-hidden">
            <CardHeader className="border-b bg-gradient-to-r from-indigo-50 to-purple-50 dark:from-indigo-950/50 dark:to-purple-950/50">
              <CardTitle className="flex items-center gap-2 text-xl">
                <Receipt className="h-5 w-5" />
                Original Bill
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              <div className="relative group">
                <img
                  src={`${API_URL}/bill/${bill_id}/view`}
                  alt="Bill"
                  className="w-full rounded-xl shadow-lg transition-transform duration-200 group-hover:scale-[1.02]"
                />
                <div className="absolute inset-0 bg-black/0 group-hover:bg-black/5 rounded-xl transition-colors duration-200" />
              </div>
            </CardContent>
          </Card>

          {/* Split Breakdown */}
          <Card className="shadow-xl border-0 bg-white/80 dark:bg-gray-900/80 backdrop-blur-xl">
            <CardHeader className="border-b bg-gradient-to-r from-indigo-50 to-purple-50 dark:from-indigo-950/50 dark:to-purple-950/50">
              <CardTitle className="flex items-center gap-2 text-xl">
                <DollarSign className="h-5 w-5" />
                Split Breakdown
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              {billData?.split_result?.breakdown ? (
                <div className="space-y-4">
                  {billData.split_result.breakdown.map((split, index) => (
                    <div
                      key={index}
                      className="flex items-center justify-between p-6 rounded-xl bg-gradient-to-r from-indigo-50 to-purple-50 dark:from-indigo-950/30 dark:to-purple-950/30 border border-indigo-100 dark:border-indigo-900 hover:shadow-md transition-all duration-200"
                    >
                      <div className="flex items-center gap-4">
                        <div className="h-12 w-12 rounded-full bg-gradient-to-br from-indigo-600 to-purple-600 flex items-center justify-center text-white font-bold text-lg shadow-lg">
                          {split.person}
                        </div>
                        <div>
                          <p className="text-lg font-semibold text-gray-900 dark:text-white">
                            Person {split.person}
                          </p>
                          <p className="text-sm text-gray-600 dark:text-gray-400">
                            Subtotal: ${split.subtotal?.toFixed(2) || '0.00'}
                          </p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-3xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 dark:from-indigo-400 dark:to-purple-400 bg-clip-text text-transparent">
                          ${split.total.toFixed(2)}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                          Total amount
                        </p>
                      </div>
                    </div>
                  ))}
                  
                  {/* JSON Toggle */}
                  <Button
                    variant="ghost"
                    onClick={() => setShowJSON(!showJSON)}
                    className="w-full mt-4 gap-2"
                  >
                    <Eye className="h-4 w-4" />
                    {showJSON ? 'Hide' : 'Show'} Raw Data
                    {showJSON ? (
                      <ChevronUp className="h-4 w-4" />
                    ) : (
                      <ChevronDown className="h-4 w-4" />
                    )}
                  </Button>
                  
                  {showJSON && (
                    <div className="mt-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-xl overflow-x-auto">
                      <pre className="text-xs font-mono text-gray-700 dark:text-gray-300">
                        {JSON.stringify(billData, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-8">
                  <p className="text-gray-500 dark:text-gray-400">
                    No split data available
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Action Buttons */}
          <div className="grid sm:grid-cols-2 gap-4">
            <Button
              onClick={downloadBill}
              size="lg"
              className="h-14 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white font-semibold shadow-lg shadow-green-500/30 dark:shadow-green-500/20"
            >
              <Download className="h-5 w-5 mr-2" />
              Download Bill
            </Button>
            <Button
              onClick={() => navigate('/')}
              variant="outline"
              size="lg"
              className="h-14 font-semibold border-2"
            >
              <Home className="h-5 w-5 mr-2" />
              Back to Home
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Result;
