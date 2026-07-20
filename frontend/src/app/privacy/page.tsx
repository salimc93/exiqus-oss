// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2025-2026 Exiqus

/* eslint-disable react/no-unescaped-entities */
'use client';

import Link from 'next/link';

export default function PrivacyPolicyPage() {
  return (
    <div className="min-h-screen bg-[#0A0A0A] py-16">
      <div className="container mx-auto max-w-4xl px-4">
        {/* Header */}
        <div className="mb-16 text-center">
          <div className="mb-6 inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-r from-indigo-500/20 to-purple-500/20">
            <svg
              className="h-8 w-8 text-indigo-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
              />
            </svg>
          </div>
          <h1 className="mb-4 bg-gradient-to-r from-white via-gray-100 to-gray-300 bg-clip-text font-bold text-4xl text-transparent">
            Privacy Policy
          </h1>
          <p className="text-gray-400 text-lg">
            How Exiqus collects, uses, and protects your personal information
          </p>
          <p className="mt-2 text-gray-500 text-sm">Last updated: September 10, 2025</p>
        </div>

        {/* Content */}
        <div className="prose prose-invert max-w-none">
          <div className="space-y-8 rounded-2xl border border-gray-800/50 bg-gray-900/50 p-8 backdrop-blur-xl">
            {/* Introduction */}
            <section>
              <h2 className="mb-4 border-gray-700/50 border-b pb-2 font-bold text-2xl text-white">
                1. Introduction
              </h2>
              <p className="mb-4 text-gray-300 leading-relaxed">
                Exiqus ("we," "our," or "us") is committed to protecting your privacy. This Privacy
                Policy explains how we collect, use, disclose, and safeguard your information when
                you use our AI-powered developer assessment platform and related services.
              </p>
              <p className="text-gray-300 leading-relaxed">
                By using Exiqus, you consent to the data practices described in this Privacy Policy.
                If you do not agree with the practices described here, please do not use our
                services.
              </p>
            </section>

            {/* Information We Collect */}
            <section>
              <h2 className="mb-4 border-gray-700/50 border-b pb-2 font-bold text-2xl text-white">
                2. Information We Collect
              </h2>

              <h3 className="mb-3 font-semibold text-white text-xl">2.1 Account Information</h3>
              <p className="mb-4 text-gray-300 leading-relaxed">
                When you create an account, we collect:
              </p>
              <ul className="mb-4 ml-4 list-inside list-disc space-y-1 text-gray-300">
                <li>Email address (required for account identification)</li>
                <li>Full name</li>
                <li>Company name (optional)</li>
                <li>Password (stored as encrypted hash)</li>
                <li>Company size, industry, and use case (optional)</li>
                <li>Communication and notification preferences</li>
              </ul>

              <h3 className="mb-3 font-semibold text-white text-xl">2.2 Analysis Data</h3>
              <p className="mb-4 text-gray-300 leading-relaxed">
                When you use our analysis services, we collect and process:
              </p>
              <ul className="mb-4 ml-4 list-inside list-disc space-y-1 text-gray-300">
                <li>Repository URLs and names you submit for analysis</li>
                <li>
                  Analysis results including technical insights, code patterns, and assessments
                </li>
                <li>Processing metadata (analysis time, token usage, API costs)</li>
                <li>Your consent preferences for data usage</li>
              </ul>

              <h3 className="mb-3 font-semibold text-white text-xl">
                2.3 Usage and Technical Information
              </h3>
              <p className="mb-4 text-gray-300 leading-relaxed">
                We automatically collect technical information including:
              </p>
              <ul className="mb-4 ml-4 list-inside list-disc space-y-1 text-gray-300">
                <li>IP addresses and geographic location</li>
                <li>Browser type and version, operating system</li>
                <li>API usage patterns and performance metrics</li>
                <li>Platform usage activities and timestamps</li>
                <li>Error logs and debugging information</li>
              </ul>

              <h3 className="mb-3 font-semibold text-white text-xl">
                2.4 Payment and Billing Information
              </h3>
              <p className="mb-4 text-gray-300 leading-relaxed">
                For paid subscriptions, we collect:
              </p>
              <ul className="mb-4 ml-4 list-inside list-disc space-y-1 text-gray-300">
                <li>Billing address and payment method details (processed by Stripe)</li>
                <li>Subscription history and usage overage records</li>
                <li>Invoice and payment transaction records</li>
              </ul>

              <h3 className="mb-3 font-semibold text-white text-xl">2.5 Communications</h3>
              <p className="mb-4 text-gray-300 leading-relaxed">When you contact us, we collect:</p>
              <ul className="mb-4 ml-4 list-inside list-disc space-y-1 text-gray-300">
                <li>Contact form messages including name, email, subject, and message content</li>
                <li>Support ticket correspondence and resolution history</li>
                <li>Priority support tracking and SLA monitoring data</li>
              </ul>
            </section>

            {/* How We Use Your Information */}
            <section>
              <h2 className="mb-4 border-gray-700/50 border-b pb-2 font-bold text-2xl text-white">
                3. How We Use Your Information
              </h2>

              <p className="mb-4 text-gray-300 leading-relaxed">
                We use collected information for the following purposes:
              </p>

              <h3 className="mb-3 font-semibold text-white text-xl">3.1 Service Provision</h3>
              <ul className="mb-4 ml-4 list-inside list-disc space-y-1 text-gray-300">
                <li>Providing AI-powered developer assessments and analysis</li>
                <li>Processing repository analysis requests and generating insights</li>
                <li>Managing user accounts and subscription services</li>
                <li>Facilitating API access and quota management</li>
              </ul>

              <h3 className="mb-3 font-semibold text-white text-xl">3.2 Platform Improvement</h3>
              <ul className="mb-4 ml-4 list-inside list-disc space-y-1 text-gray-300">
                <li>Analyzing usage patterns to improve service performance</li>
                <li>Developing and enhancing AI analysis algorithms</li>
                <li>Monitoring system health and preventing technical issues</li>
                <li>Training machine learning models (only with explicit consent)</li>
              </ul>

              <h3 className="mb-3 font-semibold text-white text-xl">3.3 Customer Support</h3>
              <ul className="mb-4 ml-4 list-inside list-disc space-y-1 text-gray-300">
                <li>Responding to customer inquiries and support requests</li>
                <li>Providing priority support based on subscription tier</li>
                <li>Troubleshooting technical issues and service problems</li>
              </ul>

              <h3 className="mb-3 font-semibold text-white text-xl">3.4 Business Operations</h3>
              <ul className="mb-4 ml-4 list-inside list-disc space-y-1 text-gray-300">
                <li>Processing payments and managing billing</li>
                <li>Preventing fraud and ensuring security</li>
                <li>Complying with legal obligations and regulations</li>
                <li>Maintaining audit trails for administrative actions</li>
              </ul>
            </section>

            {/* Data Retention */}
            <section>
              <h2 className="mb-4 border-gray-700/50 border-b pb-2 font-bold text-2xl text-white">
                4. Data Retention
              </h2>

              <p className="mb-4 text-gray-300 leading-relaxed">
                We retain different types of data for varying periods based on business needs and
                legal requirements:
              </p>

              <h3 className="mb-3 font-semibold text-white text-xl">4.1 Analysis Data</h3>
              <p className="mb-4 text-gray-300 leading-relaxed">
                Analysis results are retained indefinitely as they represent the core value of our
                service. However, you can request deletion of your analysis data at any time through
                your account settings or by contacting support.
              </p>

              <h3 className="mb-3 font-semibold text-white text-xl">4.2 Account Data</h3>
              <p className="mb-4 text-gray-300 leading-relaxed">
                Account information is retained for the duration of your account plus 30 days after
                account deletion for administrative purposes.
              </p>

              <h3 className="mb-3 font-semibold text-white text-xl">
                4.3 Usage and Technical Data
              </h3>
              <p className="mb-4 text-gray-300 leading-relaxed">
                Technical logs and usage data are typically retained for 90 days for performance
                monitoring and debugging purposes.
              </p>

              <h3 className="mb-3 font-semibold text-white text-xl">4.4 Billing Data</h3>
              <p className="mb-4 text-gray-300 leading-relaxed">
                Payment processing and billing records are managed by our payment processor, Stripe.
                Stripe retains this data according to their data retention policies and compliance
                requirements. We maintain only transaction references and subscription status in our
                systems.
              </p>
            </section>

            {/* Data Sharing and Disclosure */}
            <section>
              <h2 className="mb-4 border-gray-700/50 border-b pb-2 font-bold text-2xl text-white">
                5. Data Sharing and Disclosure
              </h2>

              <p className="mb-4 text-gray-300 leading-relaxed">
                We do not sell, trade, or otherwise transfer your personal information to third
                parties except in the following circumstances:
              </p>

              <h3 className="mb-3 font-semibold text-white text-xl">5.1 Service Providers</h3>
              <p className="mb-4 text-gray-300 leading-relaxed">
                We share information with trusted third parties who assist in operating our
                platform:
              </p>
              <ul className="mb-4 ml-4 list-inside list-disc space-y-1 text-gray-300">
                <li>Stripe for payment processing and subscription management</li>
                <li>Cloud infrastructure providers for hosting and data storage</li>
                <li>Email service providers for transactional communications</li>
                <li>AI service providers for analysis processing</li>
              </ul>

              <h3 className="mb-3 font-semibold text-white text-xl">5.2 Legal Requirements</h3>
              <p className="mb-4 text-gray-300 leading-relaxed">
                We may disclose information when required by law, court order, or government
                regulation, or to protect our rights, property, or safety.
              </p>

              <h3 className="mb-3 font-semibold text-white text-xl">5.3 Business Transfers</h3>
              <p className="mb-4 text-gray-300 leading-relaxed">
                In the event of a merger, acquisition, or asset sale, user information may be
                transferred as part of the business assets.
              </p>
            </section>

            {/* Data Security */}
            <section>
              <h2 className="mb-4 border-gray-700/50 border-b pb-2 font-bold text-2xl text-white">
                6. Data Security
              </h2>

              <p className="mb-4 text-gray-300 leading-relaxed">
                We implement industry-standard security measures to protect your information:
              </p>
              <ul className="mb-4 ml-4 list-inside list-disc space-y-1 text-gray-300">
                <li>Encryption of data in transit and at rest</li>
                <li>Secure password hashing using industry-standard algorithms</li>
                <li>Regular security audits and vulnerability assessments</li>
                <li>Access controls and authentication mechanisms</li>
                <li>API key management with proper scope and expiration</li>
                <li>Audit logging of administrative actions</li>
              </ul>

              <p className="text-gray-300 leading-relaxed">
                While we strive to protect your personal information, no method of transmission over
                the internet or electronic storage is 100% secure. We cannot guarantee absolute
                security.
              </p>
            </section>

            {/* Your Rights and Choices */}
            <section>
              <h2 className="mb-4 border-gray-700/50 border-b pb-2 font-bold text-2xl text-white">
                7. Your Rights and Choices
              </h2>

              <p className="mb-4 text-gray-300 leading-relaxed">
                You have the following rights regarding your personal information:
              </p>

              <h3 className="mb-3 font-semibold text-white text-xl">7.1 Access and Portability</h3>
              <ul className="mb-4 ml-4 list-inside list-disc space-y-1 text-gray-300">
                <li>Request a copy of your personal data</li>
                <li>Export your analysis results and account data</li>
                <li>Receive data in a portable, machine-readable format</li>
              </ul>

              <h3 className="mb-3 font-semibold text-white text-xl">7.2 Correction and Updates</h3>
              <ul className="mb-4 ml-4 list-inside list-disc space-y-1 text-gray-300">
                <li>Update your account information through your profile settings</li>
                <li>Request correction of inaccurate or incomplete data</li>
                <li>Modify your communication and privacy preferences</li>
              </ul>

              <h3 className="mb-3 font-semibold text-white text-xl">7.3 Deletion</h3>
              <ul className="mb-4 ml-4 list-inside list-disc space-y-1 text-gray-300">
                <li>Delete individual analysis results</li>
                <li>Request deletion of your entire account and associated data</li>
                <li>Withdraw consent for data processing (where applicable)</li>
              </ul>

              <h3 className="mb-3 font-semibold text-white text-xl">7.4 Processing Restrictions</h3>
              <ul className="mb-4 ml-4 list-inside list-disc space-y-1 text-gray-300">
                <li>Opt out of training data usage</li>
                <li>Restrict processing for specific purposes</li>
                <li>Object to automated decision-making</li>
              </ul>
            </section>

            {/* Cookies and Tracking */}
            <section>
              <h2 className="mb-4 border-gray-700/50 border-b pb-2 font-bold text-2xl text-white">
                8. Cookies and Tracking Technologies
              </h2>

              <p className="mb-4 text-gray-300 leading-relaxed">
                We use cookies and similar tracking technologies to enhance your experience:
              </p>

              <h3 className="mb-3 font-semibold text-white text-xl">8.1 Essential Cookies</h3>
              <p className="mb-4 text-gray-300 leading-relaxed">
                Required for the website to function properly, including authentication, security,
                and basic functionality.
              </p>

              <h3 className="mb-3 font-semibold text-white text-xl">8.2 Analytics Cookies</h3>
              <p className="mb-4 text-gray-300 leading-relaxed">
                Help us understand how users interact with our platform to improve performance and
                user experience.
              </p>

              <h3 className="mb-3 font-semibold text-white text-xl">8.3 Preference Cookies</h3>
              <p className="mb-4 text-gray-300 leading-relaxed">
                Remember your settings and preferences for future visits.
              </p>

              <p className="text-gray-300 leading-relaxed">
                You can manage your cookie preferences through our cookie consent banner or your
                browser settings. For more details, see our{' '}
                <Link href="/terms" className="text-indigo-400 underline hover:text-indigo-300">
                  Terms of Service
                </Link>
                .
              </p>
            </section>

            {/* International Data Transfers */}
            <section>
              <h2 className="mb-4 border-gray-700/50 border-b pb-2 font-bold text-2xl text-white">
                9. International Data Transfers
              </h2>

              <p className="mb-4 text-gray-300 leading-relaxed">
                Your information may be transferred to and processed in countries other than your
                country of residence. We ensure that such transfers comply with applicable data
                protection laws through:
              </p>
              <ul className="mb-4 ml-4 list-inside list-disc space-y-1 text-gray-300">
                <li>Standard contractual clauses approved by regulatory authorities</li>
                <li>Adequacy decisions where applicable</li>
                <li>Other appropriate safeguards as required by law</li>
              </ul>
            </section>

            {/* Children's Privacy */}
            <section>
              <h2 className="mb-4 border-gray-700/50 border-b pb-2 font-bold text-2xl text-white">
                10. Children's Privacy
              </h2>

              <p className="text-gray-300 leading-relaxed">
                Our services are not intended for individuals under the age of 16. We do not
                knowingly collect personal information from children under 16. If you become aware
                that a child has provided us with personal information, please contact us
                immediately.
              </p>
            </section>

            {/* Changes to Privacy Policy */}
            <section>
              <h2 className="mb-4 border-gray-700/50 border-b pb-2 font-bold text-2xl text-white">
                11. Changes to This Privacy Policy
              </h2>

              <p className="mb-4 text-gray-300 leading-relaxed">
                We may update this Privacy Policy from time to time. We will notify you of material
                changes by:
              </p>
              <ul className="mb-4 ml-4 list-inside list-disc space-y-1 text-gray-300">
                <li>Posting the updated policy on our website</li>
                <li>Updating the "Last updated" date</li>
                <li>Sending email notifications for significant changes</li>
                <li>Displaying prominent notices within the platform</li>
              </ul>

              <p className="text-gray-300 leading-relaxed">
                Your continued use of our services after changes become effective constitutes
                acceptance of the updated Privacy Policy.
              </p>
            </section>

            {/* Contact Information */}
            <section>
              <h2 className="mb-4 border-gray-700/50 border-b pb-2 font-bold text-2xl text-white">
                12. Contact Us
              </h2>

              <p className="mb-4 text-gray-300 leading-relaxed">
                If you have questions about this Privacy Policy or our data practices, please
                contact us:
              </p>

              <div className="space-y-2 rounded-lg bg-gray-800/30 p-4">
                <p className="text-gray-300">
                  <span className="font-semibold text-white">Contact:</span> via the in-app contact
                  form
                </p>
                <p className="text-gray-300">
                  <span className="font-semibold text-white">Support:</span>{' '}
                  <Link href="/contact" className="text-indigo-400 underline hover:text-indigo-300">
                    Contact Form
                  </Link>
                </p>
                <p className="text-gray-300">
                  <span className="font-semibold text-white">Privacy Inquiries:</span> the contact
                  form
                </p>
              </div>

              <p className="mt-4 text-gray-400 text-sm">
                For GDPR-related requests, please allow up to 30 days for processing. For urgent
                privacy concerns, please mark your communication as "URGENT PRIVACY REQUEST."
              </p>
            </section>

            {/* Related Links */}
            <section className="border-gray-700/50 border-t pt-8">
              <h2 className="mb-4 font-bold text-white text-xl">Related Legal Documents</h2>
              <div className="flex flex-wrap gap-4">
                <Link
                  href="/terms"
                  className="inline-flex items-center rounded-lg bg-gray-800/50 px-4 py-2 text-indigo-400 transition-all duration-200 hover:bg-gray-800 hover:text-indigo-300"
                >
                  Terms of Service
                </Link>
                <Link
                  href="/refund"
                  className="inline-flex items-center rounded-lg bg-gray-800/50 px-4 py-2 text-indigo-400 transition-all duration-200 hover:bg-gray-800 hover:text-indigo-300"
                >
                  Refund Policy
                </Link>
                <Link
                  href="/contact"
                  className="inline-flex items-center rounded-lg bg-gray-800/50 px-4 py-2 text-indigo-400 transition-all duration-200 hover:bg-gray-800 hover:text-indigo-300"
                >
                  Contact Us
                </Link>
              </div>
            </section>
          </div>
        </div>
      </div>
    </div>
  );
}
