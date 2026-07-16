"use client";

import { useState } from "react";
import { FlaskConical, ShieldCheck, Dna, Github, ExternalLink } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import PipelineTab from "@/components/masld/pipeline-tab";
import ValidationTab from "@/components/masld/validation-tab";

export default function Home() {
  const [activeTab, setActiveTab] = useState("pipeline");

  return (
    <div className="min-h-screen flex flex-col bg-background">
      <header className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-14">
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center h-8 w-8 rounded-lg bg-emerald-600 text-white">
                <Dna className="h-4 w-4" />
              </div>
              <div>
                <h1 className="text-sm font-semibold tracking-tight leading-none">
                  MASLD DrugScope
                </h1>
                <p className="text-[10px] text-muted-foreground leading-none mt-0.5">
                  GNN-Powered Therapeutic Hypothesis Engine
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="text-[10px] text-muted-foreground hidden sm:block">
                Ferroptosis-Driven Fibrosis Signature &middot; EASL-EASD-EASO Aligned
              </div>
              <a
                href="https://github.com/subhadipban-lgtm/masld-cdss"
                target="_blank"
                rel="noopener noreferrer"
                className="text-muted-foreground hover:text-foreground transition-colors"
                aria-label="View source on GitHub"
              >
                <Github className="h-4 w-4" />
              </a>
            </div>
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <Tabs
          value={activeTab}
          onValueChange={setActiveTab}
          className="w-full"
        >
          <TabsList className="grid w-full max-w-md mx-auto grid-cols-2 mb-6">
            <TabsTrigger
              value="pipeline"
              className="flex items-center gap-2 data-[state=active]:bg-emerald-600 data-[state=active]:text-white"
            >
              <FlaskConical className="h-3.5 w-3.5" />
              <span className="text-xs sm:text-sm">Pipeline</span>
            </TabsTrigger>
            <TabsTrigger
              value="validation"
              className="flex items-center gap-2 data-[state=active]:bg-emerald-600 data-[state=active]:text-white"
            >
              <ShieldCheck className="h-3.5 w-3.5" />
              <span className="text-xs sm:text-sm">Validation</span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="pipeline" className="mt-0">
            <PipelineTab />
          </TabsContent>

          <TabsContent value="validation" className="mt-0">
            <ValidationTab />
          </TabsContent>
        </Tabs>
      </main>

      <footer className="border-t border-border bg-card/50 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-muted-foreground">
            <p>
              MASLD DrugScope &mdash; Computational hypothesis-generating tool for research use only.
            </p>
            <div className="flex items-center gap-3">
              <p className="hidden sm:block">
                All predictions must be experimentally validated before any clinical interpretation.
              </p>
              <a
                href="https://github.com/subhadipban-lgtm/masld-cdss"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-border bg-card hover:bg-accent text-foreground transition-colors text-xs font-medium"
              >
                <Github className="h-3 w-3" />
                GitHub
                <ExternalLink className="h-2.5 w-2.5" />
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}